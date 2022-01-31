# This code is part of qiskit-runtime.
#
# (C) Copyright IBM 2021.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""A generalized SPSA optimizer including support for Hessians."""

from abc import ABC, abstractmethod
from typing import Iterator, Optional, Union, Callable, Tuple, List, Dict, Any
import logging
from time import time
import warnings
import sys
import json
import traceback
from collections import deque

import numpy as np
import scipy

from qiskit.algorithms.optimizers import Optimizer, OptimizerSupportLevel, SPSA, QNSPSA
from qiskit import Aer
from qiskit.algorithms import VQE, VQEResult
from qiskit.algorithms.exceptions import AlgorithmError
from qiskit.algorithms.minimum_eigen_solvers import MinimumEigensolverResult
from qiskit.circuit import ParameterVector, QuantumCircuit
from qiskit.opflow import (
    StateFn,
    CircuitSampler,
    PauliExpectation,
    ExpectationBase,
    OperatorBase,
    ListOp,
    I,
)
from qiskit.providers import BaseBackend, Backend
from qiskit.utils import QuantumInstance

from qiskit.ignis.mitigation.measurement import CompleteMeasFitter
from qiskit.providers.ibmq.runtime.utils import RuntimeDecoder

# the overlap function
OVERLAP = Callable[[np.ndarray, np.ndarray], float]

# parameters, loss, stepsize, number of function evaluations, accepted
CALLBACK = Callable[[np.ndarray, float, float, int, bool], None]

logger = logging.getLogger(__name__)


# Suppress all warnings
warnings.simplefilter("ignore")

# pylint: disable=invalid-name


# disable check for ansatzs, optimizer setter because of pylint bug
# pylint: disable=no-member
class It(ABC):
    """A base class for serializable iterators."""

    @abstractmethod
    def serialize(self) -> Tuple[str, Dict[str, Any]]:
        """Serialize the iterator."""
        raise NotImplementedError

    @abstractmethod
    def get_iterator(self) -> Iterator[float]:
        """Get the iterator."""
        raise NotImplementedError

    @staticmethod
    def deserialize(serialized: Tuple[str, Dict[str, Any]]) -> "It":
        """Construct the iterator from the serialized data."""

        name, inputs = serialized
        classes = {
            "Constant": Constant,
            "Powerlaw": Powerlaw,
            "Concatenated": Concatenated,
        }
        return classes[name](**inputs)


class Constant(It):
    """An iterator yielding constant values."""

    def __init__(self, value: float) -> None:
        """
        Args:
            value: The constant value yielded from this iterator.
        """
        self.value = value

    def get_iterator(self) -> Iterator[float]:
        def constant_it():
            while True:
                yield self.value

        return constant_it

    def serialize(self) -> Tuple[str, Dict[str, Any]]:
        return "Constant", {"value": self.value}


class Powerlaw(It):
    r"""An iterator yielding values from a powerlaw.

    The powerlaw is

    .. math::

        k(n) = c \left(\frac{1}{n + A}\right)^p,

    where :math:`c` is the constant coeffient (``coeff``), :math:`p` is the exponent
    (``power``), :math:`A` is a constant offset (``offset``) and :math:`n` is an integer.
    """

    def __init__(self, coeff, power, offset, skip=0):
        """
        Args:
            coeff: The coefficient of the powerlaw.
            power: The exponent in the powerlaw.
            offset: The offset.
            skip: How many initial values to skip in the iterator.
        """
        self.coeff = coeff
        self.power = power
        self.offset = offset
        self.skip = skip

    def serialize(self) -> Tuple[str, Dict[str, Any]]:
        return (
            "Powerlaw",
            {
                "coeff": self.coeff,
                "power": self.power,
                "offset": self.offset,
                "skip": self.skip,
            },
        )

    def get_iterator(self) -> Iterator[float]:
        def powerlaw_it():
            n = 1
            while True:
                if n > self.skip:
                    yield self.coeff / ((n + self.offset) ** self.power)
                n += 1

        return powerlaw_it


class Concatenated(It):
    """An iterator consisting of concatenated other iterators."""

    def __init__(self, iterators: List[It], breakpoints: List[int]) -> None:
        """
        Args:
            iterators: A list of iterators this iterator is made up of.
            breakpoints: A list of integers specifying when to use the next iterator.
        """
        self.iterators = []
        # deserialize if necessary
        for iterator in iterators:
            if isinstance(iterator, (list, tuple)):
                self.iterators.append(self.deserialize(iterator))
            else:
                self.iterators.append(iterator)

        self.breakpoints = breakpoints

    def serialize(self) -> Tuple[str, Dict[str, Any]]:
        return (
            "Concatenated",
            {
                "iterators": [it.serialize() for it in self.iterators],
                "breakpoints": self.breakpoints,
            },
        )

    def get_iterator(self) -> Iterator[float]:
        iterators = [it.get_iterator()() for it in self.iterators]
        breakpoints = self.breakpoints

        def concat():
            i, n = (
                0,
                0,
            )  # n counts always up, i is at which iterator/breakpoint pair we are
            while True:
                if i < len(breakpoints) and n >= breakpoints[i]:
                    i += 1
                yield next(iterators[i])
                n += 1

        return concat


class _SPSA(Optimizer):
    """A generalized SPSA optimizer including support for Hessians."""

    def __init__(
        self,
        maxiter: int = 100,
        blocking: bool = False,
        allowed_increase: Optional[float] = None,
        trust_region: bool = False,
        learning_rate: Optional[Union[float, Callable[[], Iterator]]] = None,
        perturbation: Optional[Union[float, Callable[[], Iterator]]] = None,
        resamplings: int = 1,
        last_avg: int = 1,
        callback: Optional[CALLBACK] = None,
        # 2-SPSA arguments
        second_order: bool = False,  # skip_calibration: bool = False) -> None:
        hessian_delay: int = 0,
        lse_solver: Optional[
            Union[str, Callable[[np.ndarray, np.ndarray], np.ndarray]]
        ] = None,
        regularization: Optional[float] = None,
        perturbation_dims: Optional[int] = None,
        initial_hessian: Optional[np.ndarray] = None,
        expectation: Optional[ExpectationBase] = None,
        backend: Optional[Union[Backend, QuantumInstance]] = None,
    ) -> None:
        r"""
        Args:
            maxiter: The maximum number of iterations.
            blocking: If True, only accepts updates that improve the loss.
            allowed_increase: If blocking is True, this sets by how much the loss can increase
                and still be accepted. If None, calibrated automatically to be twice the
                standard deviation of the loss function.
            trust_region: If True, restricts norm of the random direction to be <= 1.
            learning_rate: A generator yielding learning rates for the parameter updates,
                :math:`a_k`.
            perturbation: A generator yielding the perturbation magnitudes :math:`c_k`.
            resamplings: In each step, sample the gradient (and preconditioner) this many times.
            last_avg: Return the average of the ``last_avg`` parameters instead of just the
                last parameter values.
            callback: A callback function passed information in each iteration step. The
                information is, in this order: the parameters, the function value, the number
                of function evaluations, the stepsize, whether the step was accepted.
            second_order: If True, use 2-SPSA instead of SPSA. In 2-SPSA, the Hessian is estimated
                additionally to the gradient, and the gradient is preconditioned with the inverse
                of the Hessian to improve convergence.
            hessian_delay: Start preconditioning only after a certain number of iterations.
                Can be useful to first get a stable average over the last iterations before using
                the preconditioner.
            lse_solver: The method to solve for the inverse of the preconditioner. Per default an
                exact LSE solver is used, but can e.g. be overwritten by a minimization routine.
            regularization: To ensure the preconditioner is symmetric and positive definite, the
                identity times a small coefficient is added to it. This generator yields that
                coefficient.
            perturbation_dims: The number of dimensions to perturb at once. Per default all
                dimensions are perturbed simultaneously.
            initial_hessian: The initial guess for the Hessian. By default the identity matrix
                is used.
            expectation: An expectation converter.
            backend: A backend to evaluate the circuits, if the overlap function is provided as
                a circuit and the objective function as operator expression.
        """
        super().__init__()

        if regularization is None:
            regularization = 0.01

        if lse_solver is None:
            lse_solver = np.linalg.solve

        self.history = None

        self.maxiter = maxiter
        self.learning_rate = learning_rate
        self.perturbation = perturbation
        self.blocking = blocking
        self.allowed_increase = allowed_increase
        self.trust_region = trust_region
        self.callback = callback
        self.resamplings = resamplings
        self.last_avg = last_avg
        self.second_order = second_order
        self.hessian_delay = hessian_delay
        self.lse_solver = lse_solver
        self.regularization = regularization
        self.perturbation_dims = perturbation_dims
        self.initial_hessian = initial_hessian
        self.trust_region = trust_region

        # runtime arguments
        self.grad_params = None
        self.grad_expr = None
        self.hessian_params = None
        self.hessian_expr = None
        self.gradient_expressions = None

        if backend is not None:
            self._sampler = CircuitSampler(backend, caching="all")
            self._expectation = expectation
        else:
            self._sampler = None
            self._expectation = None

        self._nfev = None
        self._moving_avg = None  # moving average of the preconditioner

    @staticmethod
    def calibrate(
        loss: Callable[[np.ndarray], float],
        initial_point: np.ndarray,
        c: float = 0.1,
        stability_constant: float = 0,
        target_magnitude: Optional[float] = None,  # 2 pi / 10
        alpha: float = 0.602,
        gamma: float = 0.101,
        modelspace: bool = False,
    ) -> Tuple[Iterator[float], Iterator[float]]:
        r"""Calibrate SPSA parameters with a powerseries as learning rate and perturbation coeffs.

        The powerseries are:

        .. math::

            a_k = \frac{a}{(A + k + 1)^\alpha}, c_k = \frac{c}{(k + 1)^\gamma}

        Args:
            loss: The loss function.
            initial_point: The initial guess of the iteration.
            c: The initial perturbation magnitude.
            stability_constant: The value of `A`.
            target_magnitude: The target magnitude for the first update step.
            alpha: The exponent of the learning rate powerseries.
            gamma: The exponent of the perturbation powerseries.
            modelspace: Whether the target magnitude is the difference of parameter values
                or function values (= model space).

        Returns:
            tuple(generator, generator): A tuple of powerseries generators, the first one for the
                learning rate and the second one for the perturbation.
        """
        if target_magnitude is None:
            target_magnitude = 2 * np.pi / 10

        dim = len(initial_point)

        # compute the average magnitude of the first step
        steps = 25
        avg_magnitudes = 0
        for _ in range(steps):
            # compute the random directon
            pert = np.array([1 - 2 * np.random.binomial(1, 0.5) for _ in range(dim)])
            delta = loss(initial_point + c * pert) - loss(initial_point - c * pert)
            avg_magnitudes += np.abs(delta / (2 * c))

        avg_magnitudes /= steps

        if modelspace:
            a = target_magnitude / (avg_magnitudes ** 2)
        else:
            a = target_magnitude / avg_magnitudes

        # compute the rescaling factor for correct first learning rate
        if a < 1e-10:
            warnings.warn(f"Calibration failed, using {target_magnitude} for `a`")
            a = target_magnitude

        def learning_rate():
            return powerseries(a, alpha, stability_constant)

        def perturbation():
            return powerseries(c, gamma)

        return learning_rate, perturbation

    @staticmethod
    def estimate_stddev(
        loss: OperatorBase, initial_point: np.ndarray, avg: int = 25
    ) -> float:
        """Estimate the standard deviation of the loss function."""
        losses = [loss(initial_point) for _ in range(avg)]
        return np.std(losses)

        # values_dict = {}
        # for params in self.grad_params:
        #     values_dict.update({params[i]: [initial_point[i]] * avg})

        # # execute at once
        # sampled = self._sampler.convert(loss, params=values_dict)
        # results = np.real(sampled.eval())

    def _point_samples(self, loss, x, eps, deltas1, deltas2):
        # cache gradient epxressions
        if self.gradient_expressions is None:
            # sorted loss parameters
            sorted_params = sorted(loss.parameters, key=lambda p: p.name)

            # SPSA estimates
            theta_p = ParameterVector("th+", len(loss.parameters))
            theta_m = ParameterVector("th-", len(loss.parameters))

            # 2-SPSA estimates
            x_pp = ParameterVector("x++", len(loss.parameters))
            x_pm = ParameterVector("x+-", len(loss.parameters))
            x_mp = ParameterVector("x-+", len(loss.parameters))
            x_mm = ParameterVector("x--", len(loss.parameters))

            self.grad_expr = [
                loss.assign_parameters(dict(zip(sorted_params, theta_p))),
                loss.assign_parameters(dict(zip(sorted_params, theta_m))),
            ]
            self.grad_params = [theta_p, theta_m]

            # catch QNSPSA case. Could be put in a method to make it a bit nicer
            if self.second_order:
                if self.hessian_expr is None:
                    self.hessian_expr = [
                        loss.assign_parameters(dict(zip(sorted_params, x_pp))),
                        loss.assign_parameters(dict(zip(sorted_params, x_pm))),
                        loss.assign_parameters(dict(zip(sorted_params, x_mp))),
                        loss.assign_parameters(dict(zip(sorted_params, x_mm))),
                    ]
                    self.hessian_params = [x_pp, x_pm, x_mp, x_mm]

                self.gradient_expressions = ListOp(self.grad_expr + self.hessian_expr)
            else:
                self.gradient_expressions = ListOp(self.grad_expr)

        num_parameters = x.size
        resamplings = len(deltas1)

        # SPSA parameters
        theta_p_ = np.array([x + eps * delta1 for delta1 in deltas1])
        theta_m_ = np.array([x - eps * delta1 for delta1 in deltas1])

        # 2-SPSA parameters
        x_pp_ = np.array(
            [x + eps * (delta1 + delta2) for delta1, delta2 in zip(deltas1, deltas2)]
        )
        x_pm_ = np.array([x + eps * delta1 for delta1 in deltas1])
        x_mp_ = np.array(
            [x - eps * (delta1 - delta2) for delta1, delta2 in zip(deltas1, deltas2)]
        )
        x_mm_ = np.array([x - eps * delta1 for delta1 in deltas1])
        y_ = np.array([x for _ in deltas1])

        # build dictionary
        values_dict = {}

        if self.second_order:
            for params, value_matrix in zip(
                self.grad_params + self.hessian_params,
                [theta_p_, theta_m_, x_pp_, x_pm_, x_mp_, x_mm_, y_],
            ):
                values_dict.update(
                    {
                        params[i]: value_matrix[:, i].tolist()
                        for i in range(num_parameters)
                    }
                )
        else:
            for params, value_matrix in zip(self.grad_params, [theta_p_, theta_m_]):
                values_dict.update(
                    {
                        params[i]: value_matrix[:, i].tolist()
                        for i in range(num_parameters)
                    }
                )

        # execute at once
        sampled = self._sampler.convert(self.gradient_expressions, params=values_dict)
        results = np.real(sampled.eval())

        # put results together
        gradient_estimate = np.zeros(x.size)
        fval_estimate = 0
        for i in range(resamplings):
            self._nfev += 2
            gradient_estimate += (
                (results[i, 0] - results[i, 1]) / (2 * eps) * deltas1[0]
            )
            fval_estimate += (results[i, 0] + results[i, 1]) / 2

            if self.callback is not None:
                if self._expectation:
                    # get estimation error for the function evaluations
                    variance = np.array(
                        [
                            self._expectation.compute_variance(sampled_op)
                            for sampled_op in sampled[i][:2]
                        ]
                    )
                    shots = self._sampler.quantum_instance.run_config.shots
                    estimation_error = np.sqrt(variance / shots)
                else:
                    estimation_error = [0.0, 0.0]

                self.callback(
                    self._nfev - 1, theta_p_[i, :], results[i, 0], estimation_error[0]
                )
                self.callback(
                    self._nfev, theta_m_[i, :], results[i, 1], estimation_error[1]
                )

        hessian_estimate = np.zeros((x.size, x.size))
        if self.second_order:
            for i in range(resamplings):
                self._nfev += 4
                diff = results[i, 2] - results[i, 3]
                diff -= results[i, 4] - results[i, 5]
                diff /= 2 * eps ** 2

                rank_one = np.outer(deltas1[i], deltas2[i])
                hessian_estimate += diff * (rank_one + rank_one.T) / 2

        return (
            gradient_estimate / resamplings,
            hessian_estimate / resamplings,
            fval_estimate / resamplings,
        )

    def _compute_update(self, loss, x, k, eps):
        # compute the perturbations
        if isinstance(self.resamplings, dict):
            avg = self.resamplings.get(k, 1)
        else:
            avg = self.resamplings

        gradient = np.zeros(x.size)
        preconditioner = np.zeros((x.size, x.size))

        # accumulate the number of samples
        deltas1 = [
            bernoulli_perturbation(x.size, self.perturbation_dims) for _ in range(avg)
        ]
        deltas2 = [
            bernoulli_perturbation(x.size, self.perturbation_dims) for _ in range(avg)
        ]

        gradient, preconditioner, fval = self._point_samples(
            loss, x, eps, deltas1, deltas2
        )

        # update the exponentially smoothed average
        if self.second_order:
            smoothed = k / (k + 1) * self._moving_avg + 1 / (k + 1) * preconditioner
            self._moving_avg = smoothed

            if k > self.hessian_delay:
                # make the preconditioner SPD
                spd_preconditioner = _make_spd(smoothed, self.regularization)

                # solve for the gradient update
                gradient = np.real(self.lse_solver(spd_preconditioner, gradient))

        return gradient, fval

    def _minimize(self, loss, initial_point):
        # handle circuits case
        if not callable(loss):
            # sorted loss parameters
            sorted_params = sorted(loss.parameters, key=lambda p: p.name)

            def loss_callable(x):
                value_dict = dict(zip(sorted_params, x))
                return self._sampler.convert(loss, params=value_dict).eval().real

        else:
            loss_callable = loss

        self.history = {
            "loss": [],
            "params": [],
            "time": [],
        }

        # ensure learning rate and perturbation are set
        # this happens only here because for the calibration the loss function is required
        if self.learning_rate is None and self.perturbation is None:
            get_learning_rate, get_perturbation = self.calibrate(
                loss_callable, initial_point
            )
            eta = get_learning_rate()
            eps = get_perturbation()
        elif self.learning_rate is None or self.perturbation is None:
            raise ValueError(
                "If one of learning rate or perturbation is set, both must be set."
            )
        else:
            if isinstance(self.learning_rate, float):
                eta = constant(self.learning_rate)
            else:
                eta = self.learning_rate()

            if isinstance(self.perturbation, float):
                eps = constant(self.perturbation)
            else:
                eps = self.perturbation()

        # prepare some initials
        x = np.asarray(initial_point)

        if self.initial_hessian is None:
            self._moving_avg = np.identity(x.size)
        else:
            self._moving_avg = self.initial_hessian

        self._nfev = 0

        # if blocking is enabled we need to keep track of the function values
        if self.blocking:
            fx = loss_callable(x)

            self._nfev += 1
            if self.allowed_increase is None:
                self.allowed_increase = 2 * self.estimate_stddev(loss_callable, x)

        logger.info("=" * 30)
        logger.info("Starting SPSA optimization")
        start = time()

        # keep track of the last few steps to return their average
        last_steps = deque([x])

        for k in range(1, self.maxiter + 1):
            iteration_start = time()
            # compute update
            update, fx_next = self._compute_update(loss, x, k, next(eps))

            # trust region
            if self.trust_region:
                norm = np.linalg.norm(update)
                if norm > 1:  # stop from dividing by 0
                    update = update / norm

            # compute next parameter value
            lr = next(eta)
            update = update * lr
            x_next = x - update

            # blocking
            if self.blocking:
                fx_next = loss_callable(x_next)

                self._nfev += 1
                if (
                    fx + self.allowed_increase <= fx_next
                ):  # accept only if loss improved

                    self.history["loss"].append(fx_next)
                    self.history["params"].append(x_next)
                    self.history["time"].append(time())

                    # if self.callback is not None:
                    #     self.callback(self._nfev,  # number of function evals
                    #                   x_next,  # next parameters
                    #                   fx_next,  # loss at next parameters
                    #                   np.linalg.norm(update),  # size of the update step
                    #                   False)  # not accepted

                    logger.info(
                        "Iteration %s/%s rejected in %s.",
                        k,
                        self.maxiter + 1,
                        time() - iteration_start,
                    )
                    continue
                fx = fx_next

            logger.info(
                "Iteration %s/%s done in %s.",
                k,
                self.maxiter + 1,
                time() - iteration_start,
            )

            # if self.callback is not None:
            #     self.callback(self._nfev,  # number of function evals
            #                   x_next,  # next parameters
            #                   fx_next,  # loss at next parameters
            #                   np.linalg.norm(update),  # size of the update step
            #                   True)  # accepted

            self.history["loss"].append(fx_next)
            self.history["params"].append(x_next)
            self.history["time"].append(time())

            # update parameters
            x = x_next

            # update the list of the last ``last_avg`` parameters
            if self.last_avg > 1:
                last_steps.append(x_next)
                if len(last_steps) > self.last_avg:
                    last_steps.popleft()

        logger.info("SPSA finished in %s", time() - start)
        logger.info("=" * 30)

        if self.last_avg > 1:
            x = np.mean(last_steps, axis=0)

        return x, loss_callable(x), self._nfev

    def get_support_level(self):
        """Get the support level dictionary."""
        return {
            "gradient": OptimizerSupportLevel.ignored,  # could be supported though
            "bounds": OptimizerSupportLevel.ignored,
            "initial_point": OptimizerSupportLevel.required,
        }

    def optimize(
        self,
        num_vars,
        objective_function,
        gradient_function=None,
        variable_bounds=None,
        initial_point=None,
    ):
        return self._minimize(objective_function, initial_point)


class _QNSPSA(_SPSA):
    """Quantum Natural SPSA."""

    def __init__(
        self,
        overlap_fn: Union[OVERLAP, QuantumCircuit],
        maxiter: int = 100,
        blocking: bool = False,
        allowed_increase: Optional[float] = None,
        learning_rate: Optional[Union[float, Callable[[], Iterator]]] = None,
        perturbation: Optional[Union[float, Callable[[], Iterator]]] = None,
        resamplings: int = 1,
        callback: Optional[CALLBACK] = None,
        # 2-SPSA arguments
        hessian_delay: int = 0,
        lse_solver: Optional[
            Union[str, Callable[[np.ndarray, np.ndarray], np.ndarray]]
        ] = None,
        regularization: Optional[float] = None,
        perturbation_dims: Optional[int] = None,
        initial_hessian: Optional[np.ndarray] = None,
        expectation: Optional[ExpectationBase] = None,
        backend: Optional[Union[Backend, QuantumInstance]] = None,
    ) -> None:
        r"""
        Args:
            maxiter: The maximum number of iterations.
            blocking: If True, only accepts updates that improve the loss.
            allowed_increase: If blocking is True, this sets by how much the loss can increase
                and still be accepted. If None, calibrated automatically to be twice the
                standard deviation of the loss function.
            learning_rate: A generator yielding learning rates for the parameter updates,
                :math:`a_k`.
            perturbation: A generator yielding the perturbation magnitudes :math:`c_k`.
            resamplings: In each step, sample the gradient (and preconditioner) this many times.
            callback: A callback function passed information in each iteration step. The
                information is, in this order: the parameters, the function value, the number
                of function evaluations, the stepsize, whether the step was accepted.
            hessian_delay: Start preconditioning only after a certain number of iterations.
                Can be useful to first get a stable average over the last iterations before using
                the preconditioner.
            lse_solver: The method to solve for the inverse of the preconditioner. Per default an
                exact LSE solver is used, but can e.g. be overwritten by a minimization routine.
            regularization: To ensure the preconditioner is symmetric and positive definite, the
                identity times a small coefficient is added to it. This generator yields that
                coefficient.
            perturbation_dims: The number of dimensions to perturb at once. Per default all
                dimensions are perturbed simulatneously.
            initial_hessian: The initial guess for the Hessian. By default the identity matrix
                is used.
            expectation: The Expectation converter for taking the average value of the
                Observable over the ansatz state function.
            backend: A backend to evaluate the circuits, if the overlap function is provided as
                a circuit and the objective function as operator expression.
        """
        super().__init__(
            maxiter,
            blocking,
            allowed_increase,
            trust_region=False,
            learning_rate=learning_rate,
            perturbation=perturbation,
            resamplings=resamplings,
            callback=callback,
            second_order=True,
            hessian_delay=hessian_delay,
            lse_solver=lse_solver,
            regularization=regularization,
            perturbation_dims=perturbation_dims,
            initial_hessian=initial_hessian,
            expectation=expectation,
            backend=backend,
        )

        self.overlap_fn = overlap_fn

        if not callable(overlap_fn):
            sorted_overlap_params = sorted(overlap_fn.parameters, key=lambda p: p.name)

            x_pp = ParameterVector("x++", overlap_fn.num_parameters)
            x_pm = ParameterVector("x+-", overlap_fn.num_parameters)
            x_mp = ParameterVector("x-+", overlap_fn.num_parameters)
            x_mm = ParameterVector("x--", overlap_fn.num_parameters)
            y = ParameterVector("y", overlap_fn.num_parameters)

            left = overlap_fn.assign_parameters(dict(zip(sorted_overlap_params, y)))
            rights = [
                overlap_fn.assign_parameters(dict(zip(sorted_overlap_params, x_pp))),
                overlap_fn.assign_parameters(dict(zip(sorted_overlap_params, x_pm))),
                overlap_fn.assign_parameters(dict(zip(sorted_overlap_params, x_mp))),
                overlap_fn.assign_parameters(dict(zip(sorted_overlap_params, x_mm))),
            ]

            self.hessian_params = [x_pp, x_pm, x_mp, x_mm, y]
            self.hessian_expr = [~StateFn(left) @ StateFn(right) for right in rights]

    @staticmethod
    def get_overlap(circuit, backend=None, expectation=None):
        """Get the overlap function."""
        params_x = ParameterVector("x", circuit.num_parameters)
        params_y = ParameterVector("y", circuit.num_parameters)

        expression = ~StateFn(circuit.assign_parameters(params_x)) @ StateFn(
            circuit.assign_parameters(params_y)
        )

        if expectation is not None:
            expression = expectation.convert(expression)

        if backend is None:

            def overlap_fn(values_x, values_y):
                value_dict = dict(
                    zip(
                        params_x[:] + params_y[:], values_x.tolist() + values_y.tolist()
                    )
                )
                return -0.5 * np.abs(expression.bind_parameters(value_dict).eval()) ** 2

        else:
            sampler = CircuitSampler(backend)

            def overlap_fn(values_x, values_y):
                value_dict = dict(
                    zip(
                        params_x[:] + params_y[:], values_x.tolist() + values_y.tolist()
                    )
                )
                return (
                    -0.5
                    * np.abs(sampler.convert(expression, params=value_dict).eval()) ** 2
                )

        return overlap_fn


class QNSPSAVQE(VQE):
    def __init__(
        self,
        ansatz: Optional[QuantumCircuit] = None,
        initial_point: Optional[np.ndarray] = None,
        expectation: Optional[ExpectationBase] = None,
        callback: Optional[Callable[[int, np.ndarray, float, float], None]] = None,
        quantum_instance: Optional[Union[QuantumInstance, BaseBackend, Backend]] = None,
        natural_spsa: bool = False,
        maxiter: int = 100,
        blocking: bool = True,
        allowed_increase: float = 0.1,
        learning_rate: Optional[float] = None,
        perturbation: Optional[float] = None,
        regularization: float = 0.01,
        resamplings: int = 1,
        hessian_delay: int = 0,
        initial_hessian: Optional[np.ndarray] = None,
    ) -> None:
        """
        Args:
            ansatz: A parameterized circuit used as Ansatz for the wave function.
            initial_point: An optional initial point (i.e. initial parameter values)
                for the optimizer. If ``None`` then VQE will look to the variational form for a
                preferred point and if not will simply compute a random one.
            expectation: The Expectation converter for taking the average value of the
                Observable over the ansatz state function. When ``None`` (the default) an
                :class:`~qiskit.opflow.expectations.ExpectationFactory` is used to select
                an appropriate expectation based on the operator and backend. When using Aer
                qasm_simulator backend, with paulis, it is however much faster to leverage custom
                Aer function for the computation but, although VQE performs much faster
                with it, the outcome is ideal, with no shot noise, like using a state vector
                simulator. If you are just looking for the quickest performance when choosing Aer
                qasm_simulator and the lack of shot noise is not an issue then set `include_custom`
                parameter here to ``True`` (defaults to ``False``).
            callback: a callback that can access the intermediate data during the optimization.
                Four parameter values are passed to the callback as follows during each evaluation
                by the optimizer for its current set of parameters as it works towards the minimum.
                These are: the evaluation count, the optimizer parameters for the
                variational form, the evaluated mean and the evaluated standard deviation.`
            quantum_instance: Quantum Instance or Backend
        """
        super().__init__(
            ansatz=ansatz,
            initial_point=initial_point,
            quantum_instance=quantum_instance,
            expectation=expectation,
        )

        self.natural_spsa = natural_spsa
        self.maxiter = maxiter
        self.learning_rate = learning_rate
        self.perturbation = perturbation
        self.allowed_increase = allowed_increase
        self.blocking = blocking
        self.regularization = regularization
        self.resamplings = resamplings
        self.hessian_delay = hessian_delay
        self.initial_hessian = initial_hessian

        self._ret = VQEResult()
        self._eval_time = None
        self._callback = callback

        self._eval_count = 0

    @property
    def optimizer(self):  # pylint: disable=arguments-differ
        raise NotImplementedError(
            "The optimizer is a SPSA version with batched circuits and "
            "cannot be returned as a standalone."
        )

    @optimizer.setter
    def optimizer(self, optimizer):
        raise NotImplementedError(
            "The optimizer is a SPSA version with batched circuits and "
            "cannot be set."
        )

    def compute_minimum_eigenvalue(
        self,
        operator: OperatorBase,
        aux_operators: Optional[List[Optional[OperatorBase]]] = None,
    ) -> MinimumEigensolverResult:
        if self.quantum_instance is None:
            raise AlgorithmError(
                "A QuantumInstance or Backend "
                "must be supplied to run the quantum algorithm."
            )
        self.quantum_instance.circuit_summary = True

        if operator is None:
            raise AlgorithmError("The operator was never provided.")

        self._check_operator_ansatz(operator)

        # We need to handle the array entries being Optional i.e. having value None
        if aux_operators:
            zero_op = I.tensorpower(operator.num_qubits) * 0.0
            converted = []
            for op in aux_operators:
                if op is None:
                    converted.append(zero_op)
                else:
                    converted.append(op)

            # For some reason Chemistry passes aux_ops with 0 qubits and paulis sometimes.
            aux_operators = [zero_op if op == 0 else op for op in converted]
        else:
            aux_operators = None

        optimizer_settings = {
            "maxiter": self.maxiter,
            "blocking": self.blocking,
            "allowed_increase": self.allowed_increase,
            "learning_rate": self.learning_rate,
            "perturbation": self.perturbation,
            "regularization": self.regularization,
            "resamplings": self.resamplings,
            "hessian_delay": self.hessian_delay,
            "initial_hessian": self.initial_hessian,
            "expectation": self.expectation,
            "callback": self._callback,
            "backend": self._quantum_instance,
        }

        if self.natural_spsa:
            optimizer = _QNSPSA(overlap_fn=self.ansatz, **optimizer_settings)
        else:
            optimizer = _SPSA(**optimizer_settings)

        self._eval_count = 0
        # energy_evaluation, expectation = self.get_energy_evaluation(
        #     operator, return_expectation=True
        # )

        theta = ParameterVector("θ​", self.ansatz.num_parameters)
        energy_expectation, expectation = self.construct_expectation(
            theta, operator, return_expectation=True
        )

        start_time = time()
        opt_params, opt_value, nfev = optimizer.optimize(
            num_vars=len(self.initial_point),
            objective_function=energy_expectation,
            # gradient_function=gradient,
            # variable_bounds=bounds,
            initial_point=self.initial_point,
        )
        eval_time = time() - start_time

        result = VQEResult()
        result.optimal_point = opt_params
        result.optimal_parameters = dict(zip(self._ansatz_params, opt_params))
        result.optimal_value = opt_value
        result.cost_function_evals = nfev
        result.optimizer_time = eval_time
        result.eigenvalue = opt_value + 0j
        result.eigenstate = self._get_eigenstate(result.optimal_parameters)

        logger.info(
            "Optimization complete in %s seconds.\nFound opt_params %s in %s evals",
            eval_time,
            result.optimal_point,
            self._eval_count,
        )

        # TODO delete as soon as get_optimal_vector etc are removed
        self._ret = result

        if aux_operators is not None:
            aux_values = self._eval_aux_ops(
                opt_params, aux_operators, expectation=expectation
            )
            result.aux_operator_eigenvalues = aux_values[0]

        # return result, None

        return result, optimizer.history


# Code from qn-spsa/utils.py


def bernoulli_perturbation(dim, perturbation_dims=None):
    """Get a Bernoulli random perturbation."""
    if perturbation_dims is None:
        return np.array([1 - 2 * np.random.binomial(1, 0.5) for _ in range(dim)])

    pert = np.array(
        [1 - 2 * np.random.binomial(1, 0.5) for _ in range(perturbation_dims)]
    )
    indices = np.random.choice(list(range(dim)), size=perturbation_dims, replace=False)
    result = np.zeros(dim)
    result[indices] = pert

    return result


def powerseries(eta=0.01, power=2, offset=0):
    """Yield a series decreasing by a powerlaw."""

    n = 1
    while True:
        yield eta / ((n + offset) ** power)
        n += 1


def constant(eta=0.01):
    """Yield a constant series."""

    while True:
        yield eta


def _make_spd(matrix, bias=0.01):
    identity = np.identity(matrix.shape[0])
    psd = scipy.linalg.sqrtm(matrix.dot(matrix))
    return (1 - bias) * psd + bias * identity


class Publisher:
    """Class used to publish interim results."""

    def __init__(self, messenger):
        self._messenger = messenger

    def callback(self, *args, **kwargs):
        text = list(args)
        for k, v in kwargs.items():
            text.append({k: v})
        self._messenger.publish(text)


def _parse_optimizer(kwargs):
    optimizer = kwargs.get("optimizer", SPSA())
    # backwards compatibility: previously optimizers were dicts
    if isinstance(optimizer, dict):
        # verify the optimizer and split into name and parameters
        optimizer_name = optimizer.pop("name", "SPSA")
        if optimizer_name not in ["SPSA", "QN-SPSA"]:
            raise ValueError(
                f"Unsupported optimizer: {optimizer_name}."
                "If specified via dict only SPSA and QN-SPSA are available."
            )

        optimizer_params = optimizer

        # de-serialize learning rate and perturbation if necessary
        for attr in ["learning_rate", "perturbation"]:
            if attr in optimizer_params.keys():
                if isinstance(
                    optimizer_params[attr], (list, tuple)
                ):  # need to de-serialize
                    iterator_factory = It.deserialize(optimizer_params[attr])
                    optimizer_params[attr] = iterator_factory.get_iterator()

        if optimizer_name == "SPSA":
            optimizer = _SPSA(**optimizer_params)
        else:
            optimizer = _QNSPSA(overlap_fn=lambda: None, **optimizer_params)

    return optimizer


def main(backend, user_messenger, **kwargs):
    """Entry function."""
    # parse inputs
    mandatory = {"ansatz", "operator"}
    missing = mandatory - set(kwargs.keys())
    if len(missing) > 0:
        raise ValueError(f"The following mandatory arguments are missing: {missing}.")

    ansatz = kwargs["ansatz"]
    operator = kwargs["operator"]
    aux_operators = kwargs.get("aux_operators", None)
    initial_point = kwargs.get("initial_point", None)
    optimizer = _parse_optimizer(kwargs)

    shots = kwargs.get("shots", 1024)
    measurement_error_mitigation = kwargs.get("measurement_error_mitigation", False)

    # set up quantum instance
    if measurement_error_mitigation:
        _quantum_instance = QuantumInstance(
            backend,
            shots=shots,
            measurement_error_mitigation_shots=shots,
            measurement_error_mitigation_cls=CompleteMeasFitter,
        )
    else:
        _quantum_instance = QuantumInstance(backend, shots=shots)

    publisher = Publisher(user_messenger)

    # verify the initial point
    if initial_point == "random" or initial_point is None:
        initial_point = np.random.random(ansatz.num_parameters)
    elif len(initial_point) != ansatz.num_parameters:
        raise ValueError(
            "Mismatching number of parameters and initial point dimension."
        )

    # construct the VQE instance
    if isinstance(optimizer, (SPSA, QNSPSA, _SPSA, _QNSPSA)):
        vqe = QNSPSAVQE(
            ansatz=ansatz,
            initial_point=initial_point,
            expectation=PauliExpectation(),
            callback=publisher.callback,
            quantum_instance=_quantum_instance,
            natural_spsa=isinstance(optimizer, QNSPSA),
            allowed_increase=optimizer.allowed_increase,
            maxiter=optimizer.maxiter,
            blocking=optimizer.blocking,
            learning_rate=optimizer.learning_rate,
            perturbation=optimizer.perturbation,
            resamplings=optimizer.resamplings,
            regularization=optimizer.regularization,
            hessian_delay=optimizer.hessian_delay,
            initial_hessian=optimizer.initial_hessian,
        )
        result, history = vqe.compute_minimum_eigenvalue(operator, aux_operators)
    else:
        vqe = VQE(
            ansatz=ansatz,
            initial_point=initial_point,
            expectation=PauliExpectation(),
            callback=publisher.callback,
            quantum_instance=_quantum_instance,
        )
        result = vqe.compute_minimum_eigenvalue(operator, aux_operators)
        history = None

    eigenvalues_list = (
        result.aux_operator_eigenvalues.tolist()
        if result.aux_operator_eigenvalues is not None
        else None
    )

    serialized_result = {
        "optimizer_evals": result.optimizer_evals,
        "optimizer_time": result.optimizer_time,
        "optimal_value": result.optimal_value,
        "optimal_point": result.optimal_point,
        "optimal_parameters": None,  # ParameterVectorElement is not serializable
        "cost_function_evals": result.cost_function_evals,
        "eigenstate": result.eigenstate,
        "eigenvalue": result.eigenvalue,
        "aux_operator_eigenvalues": eigenvalues_list,
        "optimizer_history": history,
    }

    user_messenger.publish(serialized_result, final=True)


if __name__ == "__main__":
    # the code currently uses Aer instead of runtime provider
    _backend = Aer.get_backend("qasm_simulator")
    user_params = {}
    if len(sys.argv) > 1:
        # If there are user parameters.
        user_params = json.loads(sys.argv[1], cls=RuntimeDecoder)
    try:
        main(_backend, **user_params)
    except Exception:
        print(traceback.format_exc())
