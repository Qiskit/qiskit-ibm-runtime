# This code is part of Qiskit.
#
# (C) Copyright IBM 2022.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Estimator primitive."""

from __future__ import annotations
import os
from typing import Optional, Dict, Sequence, Any, Union, Mapping
import logging

import numpy as np
from numpy.typing import ArrayLike

from qiskit.circuit import QuantumCircuit
from qiskit.quantum_info.operators.base_operator import BaseOperator
from qiskit.primitives import BaseEstimator
from qiskit.primitives.base.base_primitive import _isreal
from qiskit.quantum_info import SparsePauliOp, Pauli
from qiskit.primitives.utils import init_observable
from qiskit.circuit import Parameter

# TODO import _circuit_key from terra once 0.23 is released
from .runtime_job import RuntimeJob
from .ibm_backend import IBMBackend
from .options import Options
from .base_primitive import BasePrimitive
from .utils.qctrl import validate as qctrl_validate
from .utils.deprecation import issue_deprecation_msg

# pylint: disable=unused-import,cyclic-import
from .session import Session

logger = logging.getLogger(__name__)


BasisObservableLike = Union[str, Pauli, SparsePauliOp, Mapping[Union[str, Pauli], complex]]
"""Types that can be natively used to construct a :const:`BasisObservable`."""

ObservablesArrayLike = Union[ArrayLike, Sequence[BasisObservableLike], BasisObservableLike]

ParameterMappingLike = Mapping[
    Parameter, Union[float, np.ndarray, Sequence[float], Sequence[Sequence[float]]]
]
BindingsArrayLike = Union[
    float,
    np.ndarray,
    ParameterMappingLike,
    Sequence[Union[float, Sequence[float], np.ndarray, ParameterMappingLike]],
]
"""Parameter types that can be bound to a single circuit."""


class Estimator(BasePrimitive, BaseEstimator):
    """Class for interacting with Qiskit Runtime Estimator primitive service.

    Qiskit Runtime Estimator primitive service estimates expectation values of quantum circuits and
    observables.

    The :meth:`run` can be used to submit circuits, observables, and parameters
    to the Estimator primitive.

    You are encouraged to use :class:`~qiskit_ibm_runtime.Session` to open a session,
    during which you can invoke one or more primitives. Jobs submitted within a session
    are prioritized by the scheduler, and data is cached for efficiency.

    Example::

        from qiskit.circuit.library import RealAmplitudes
        from qiskit.quantum_info import SparsePauliOp

        from qiskit_ibm_runtime import QiskitRuntimeService, Estimator

        service = QiskitRuntimeService(channel="ibm_cloud")

        psi1 = RealAmplitudes(num_qubits=2, reps=2)

        H1 = SparsePauliOp.from_list([("II", 1), ("IZ", 2), ("XI", 3)])
        H2 = SparsePauliOp.from_list([("IZ", 1)])
        H3 = SparsePauliOp.from_list([("ZI", 1), ("ZZ", 1)])

        with Session(service=service, backend="ibmq_qasm_simulator") as session:
            estimator = Estimator(session=session)

            theta1 = [0, 1, 1, 2, 3, 5]

            # calculate [ <psi1(theta1)|H1|psi1(theta1)> ]
            psi1_H1 = estimator.run(circuits=[psi1], observables=[H1], parameter_values=[theta1])
            print(psi1_H1.result())

            # calculate [ <psi1(theta1)|H2|psi1(theta1)>, <psi1(theta1)|H3|psi1(theta1)> ]
            psi1_H23 = estimator.run(
                circuits=[psi1, psi1],
                observables=[H2, H3],
                parameter_values=[theta1]*2
            )
            print(psi1_H23.result())
            # Close the session only if all jobs are finished
            # and you don't need to run more in the session
            session.close()
    """

    _PROGRAM_ID = "estimator"
    _ALLOWED_BASIS: str = "IXYZ"

    def __init__(
        self,
        backend: Optional[Union[str, IBMBackend]] = None,
        session: Optional[Union[Session, str, IBMBackend]] = None,
        options: Optional[Union[Dict, Options]] = None,
    ):
        """Initializes the Estimator primitive.

        Args:
            backend: Backend to run the primitive. This can be a backend name or an :class:`IBMBackend`
                instance. If a name is specified, the default account (e.g. ``QiskitRuntimeService()``)
                is used.

            session: Session in which to call the primitive.

                If both ``session`` and ``backend`` are specified, ``session`` takes precedence.
                If neither is specified, and the primitive is created inside a
                :class:`qiskit_ibm_runtime.Session` context manager, then the session is used.
                Otherwise if IBM Cloud channel is used, a default backend is selected.

            options: Primitive options, see :class:`Options` for detailed description.
                The ``backend`` keyword is still supported but is deprecated.
        """
        # `self._options` in this class is a Dict.
        # The base class, however, uses a `_run_options` which is an instance of
        # qiskit.providers.Options. We largely ignore this _run_options because we use
        # a nested dictionary to categorize options.
        BaseEstimator.__init__(self)
        BasePrimitive.__init__(self, backend=backend, session=session, options=options)

    def run(  # pylint: disable=arguments-differ
        self,
        circuits: QuantumCircuit | Sequence[QuantumCircuit],
        observables: Sequence[ObservablesArrayLike]
        | ObservablesArrayLike
        | Sequence[BaseOperator]
        | BaseOperator,
        parameter_values: BindingsArrayLike | Sequence[BindingsArrayLike] | None = None,
        **kwargs: Any,
    ) -> RuntimeJob:
        """Submit a request to the estimator primitive.

        Args:
            circuits: a (parameterized) :class:`~qiskit.circuit.QuantumCircuit` or
                a list of (parameterized) :class:`~qiskit.circuit.QuantumCircuit`.

            observables: Observable objects.

            parameter_values: Concrete parameters to be bound.

            **kwargs: Individual options to overwrite the default primitive options.
                These include the runtime options in :class:`qiskit_ibm_runtime.RuntimeOptions`.

        Returns:
            Submitted job.
            The result of the job is an instance of :class:`qiskit.primitives.EstimatorResult`.

        Raises:
            ValueError: Invalid arguments are given.
        """
        # To bypass base class merging of options.
        user_kwargs = {"_user_kwargs": kwargs}
        return super().run(
            circuits=circuits,
            observables=observables,
            parameter_values=parameter_values,
            **user_kwargs,
        )

    def _run(  # pylint: disable=arguments-differ
        self,
        circuits: Sequence[QuantumCircuit],
        observables: Sequence[ObservablesArrayLike],
        parameter_values: Sequence[Sequence[float]],
        **kwargs: Any,
    ) -> RuntimeJob:
        """Submit a request to the estimator primitive.

        Args:
            circuits: a (parameterized) :class:`~qiskit.circuit.QuantumCircuit` or
                a list of (parameterized) :class:`~qiskit.circuit.QuantumCircuit`.

            observables: A list of observable objects.

            parameter_values: An optional list of concrete parameters to be bound.

            **kwargs: Individual options to overwrite the default primitive options.
                These include the runtime options in :class:`~qiskit_ibm_runtime.RuntimeOptions`.

        Returns:
            Submitted job
        """
        inputs = {
            "circuits": circuits,
            "circuit_indices": list(range(len(circuits))),
            "observables": observables,
            "observable_indices": list(range(len(observables))),
            "parameters": [circ.parameters for circ in circuits],
            "parameter_values": parameter_values,
        }
        return self._run_primitive(
            primitive_inputs=inputs, user_kwargs=kwargs.get("_user_kwargs", {})
        )

    def _validate_options(self, options: dict) -> None:
        """Validate that program inputs (options) are valid
        Raises:
            ValueError: if resilience_level is out of the allowed range.
            ValueError: if resilience_level==3, backend is simulator and no coupling map
        """
        if os.getenv("QISKIT_RUNTIME_SKIP_OPTIONS_VALIDATION"):
            return

        if self._service._channel_strategy == "q-ctrl":
            qctrl_validate(options)
            return

        if not options.get("resilience_level") in list(
            range(Options._MAX_RESILIENCE_LEVEL_ESTIMATOR + 1)
        ):
            raise ValueError(
                f"resilience_level can only take the values "
                f"{list(range(Options._MAX_RESILIENCE_LEVEL_ESTIMATOR + 1))} in Estimator"
            )

        if (
            options.get("resilience_level") == 3
            and self._backend
            and self._backend.configuration().simulator
        ):
            if not options.get("simulator").get("coupling_map"):
                raise ValueError(
                    "When the backend is a simulator and resilience_level == 3,"
                    "a coupling map is required."
                )
        Options.validate_options(options)

    @staticmethod
    def _validate_observables(
        observables: Sequence[ObservablesArrayLike] | ObservablesArrayLike,
    ) -> Sequence[ObservablesArrayLike]:
        def _check_and_init(obs: Any) -> Any:
            if isinstance(obs, str):
                pass
                if not all(basis in Estimator._ALLOWED_BASIS for basis in obs):
                    raise ValueError(
                        f"Invalid character(s) found in observable string. "
                        f"Allowed basis are {Estimator._ALLOWED_BASIS}."
                    )
            elif isinstance(obs, Sequence):
                return tuple(_check_and_init(obs_) for obs_ in obs)
            elif not isinstance(obs, (Pauli, SparsePauliOp)) and isinstance(obs, BaseOperator):
                issue_deprecation_msg(
                    msg="Only Pauli and SparsePauliOp operators can be used as observables.",
                    version=0.13,
                    remedy="",
                )
                return init_observable(obs)
            elif isinstance(obs, Mapping):
                for key in obs.keys():
                    _check_and_init(key)

            return obs

        if isinstance(observables, str) or not isinstance(observables, Sequence):
            observables = (observables,)

        if len(observables) == 0:
            raise ValueError("No observables were provided.")

        return tuple(_check_and_init(obs_array) for obs_array in observables)

    @staticmethod
    def _validate_parameter_values(
        parameter_values: BindingsArrayLike | Sequence[BindingsArrayLike] | None,
        default: Sequence[Sequence[float]] | Sequence[float] | None = None,
    ) -> Sequence:

        # Allow optional (if default)
        if parameter_values is None:
            if default is None:
                raise ValueError("No default `parameter_values`, optional input disallowed.")
            parameter_values = default

        # Support numpy ndarray
        if isinstance(parameter_values, np.ndarray):
            parameter_values = parameter_values.tolist()
        elif isinstance(parameter_values, Sequence):
            parameter_values = tuple(
                vector.tolist() if isinstance(vector, np.ndarray) else vector
                for vector in parameter_values
            )

        # Allow single value
        if _isreal(parameter_values):
            parameter_values = ((parameter_values,),)
        elif isinstance(parameter_values, Sequence) and not any(
            isinstance(vector, (Sequence, Mapping)) for vector in parameter_values
        ):
            parameter_values = (parameter_values,)
        elif isinstance(parameter_values, Mapping):
            parameter_values = (parameter_values,)

        return parameter_values

    @staticmethod
    def _cross_validate_circuits_parameter_values(
        circuits: tuple[QuantumCircuit, ...], parameter_values: tuple[tuple[float, ...], ...]
    ) -> None:
        if len(circuits) != len(parameter_values):
            raise ValueError(
                f"The number of circuits ({len(circuits)}) does not match "
                f"the number of parameter value sets ({len(parameter_values)})."
            )

    @staticmethod
    def _cross_validate_circuits_observables(
        circuits: tuple[QuantumCircuit, ...], observables: tuple[ObservablesArrayLike, ...]
    ) -> None:
        if len(circuits) != len(observables):
            raise ValueError(
                f"The number of circuits ({len(circuits)}) does not match "
                f"the number of observables ({len(observables)})."
            )

    @classmethod
    def _program_id(cls) -> str:
        """Return the program ID."""
        return "estimator"
