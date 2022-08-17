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
import copy
from typing import Iterable, Optional, Dict, Sequence, Any, Union

import numpy as np
from qiskit.circuit import QuantumCircuit, Parameter
from qiskit.quantum_info import SparsePauliOp
from qiskit.opflow import PauliSumOp
from qiskit.quantum_info.operators.base_operator import BaseOperator

# pylint: disable=unused-import,cyclic-import
import qiskit_ibm_runtime.session as session_pkg

# TODO import BaseEstimator and EstimatorResult from terra once released
from .qiskit.primitives import BaseEstimator, EstimatorResult
from .qiskit_runtime_service import QiskitRuntimeService
from .program.result_decoder import ResultDecoder
from .runtime_job import RuntimeJob
from .utils.deprecation import deprecate_arguments, issue_deprecation_msg
from .runtime_options import RuntimeOptions
from .options import Options

# pylint: disable=unused-import,cyclic-import
from .session import Session


class Estimator(BaseEstimator):
    """Class for interacting with Qiskit Runtime Estimator primitive service.

    Qiskit Runtime Estimator primitive service estimates expectation values of quantum circuits and
    observables.

    The :meth:`run` can be used to submit circuits, observables, and parameters
    to the Estimator primitive.

    You are encouraged to use :class:`~qiskit_ibm_runtime.Session` to open a session,
    during which you can invoke one or more primitive programs. Jobs submitted within a session
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

        with Session(service) as session:
            estimator = Estimator(session=session)
            estimator.options.backend = 'ibmq_qasm_simulator'

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
    """

    _PROGRAM_ID = "estimator"

    def __init__(
        self,
        circuits: Optional[Union[QuantumCircuit, Iterable[QuantumCircuit]]] = None,
        observables: Optional[Iterable[SparsePauliOp]] = None,
        parameters: Optional[Iterable[Iterable[Parameter]]] = None,
        service: Optional[QiskitRuntimeService] = None,
        session: Optional[Session] = None,
        options: Optional[Union[Dict, RuntimeOptions, Options]] = None,
        skip_transpilation: Optional[bool] = False,
    ):
        """Initializes the Estimator primitive.

        Args:
            circuits: (DEPRECATED) A (parameterized) :class:`~qiskit.circuit.QuantumCircuit` or
                a list of (parameterized) :class:`~qiskit.circuit.QuantumCircuit`.

            observables: (DEPRECATED) A list of :class:`~qiskit.quantum_info.SparsePauliOp`

            parameters: (DEPRECATED) A list of parameters of the quantum circuits.
                (:class:`~qiskit.circuit.parametertable.ParameterView` or
                a list of :class:`~qiskit.circuit.Parameter`) specifying the order
                in which parameter values will be bound.

            service: (DEPRECATED) Optional instance of
                :class:`qiskit_ibm_runtime.QiskitRuntimeService` class,
                defaults to `QiskitRuntimeService()` which tries to initialize your default
                saved account.

            session: Session in which to call the sampler primitive. If ``None``, a new session
                is created using the default saved account.

            options: Primitive options, see :class:`Options` for detailed description.

            skip_transpilation: (DEPRECATED) Transpilation is skipped if set to True. False by default.
                Ignored ``skip_transpilation`` is also specified in ``options``.
        """
        super().__init__(
            circuits=circuits,
            observables=observables,
            parameters=parameters,
        )

        # TODO: Remove deprecation warnings if done in base class
        if circuits or parameters or observables:
            deprecate_arguments(
                "circuits, parameters, and observables",
                "0.7",
                f"You can instead specify these inputs using the {self.__class__.__name__}.run method.",
            )
        if skip_transpilation:
            deprecate_arguments(
                "skip_transpilation",
                "0.7",
                "Instead, use the skip_transpilation keyword argument in transpilation_settings.",
            )
        if service:
            deprecate_arguments(
                "service", "0.7", "Please use the session parameter instead."
            )

        if options is None:
            self.options = Options()
        elif isinstance(options, Options):
            self.options = copy.deepcopy(options)
            skip_transpilation = self.options.transpilation.skip_transpilation
        elif isinstance(options, RuntimeOptions):
            self.options = options._to_new_options()
        else:
            self.options = Options._from_dict(options)
            skip_transpilation = options.get("transpilation", {}).get(
                "skip_transpilation", False
            )
        self.options.transpilation.skip_transpilation = skip_transpilation

        self._initial_inputs = {
            "circuits": circuits,
            "observables": observables,
            "parameters": parameters,
        }

        if session:
            self._session = session
        else:
            if (
                session_pkg._DEFAULT_SESSION is None
                or not session_pkg._DEFAULT_SESSION._active
            ):
                session_pkg._DEFAULT_SESSION = Session(service=service)
            self._session = session_pkg._DEFAULT_SESSION

    def run(
        self,
        circuits: Union[QuantumCircuit, Sequence[QuantumCircuit]],
        observables: Sequence[BaseOperator | PauliSumOp],
        parameter_values: Optional[
            Union[Sequence[float], Sequence[Sequence[float]]]
        ] = None,
        parameters: Sequence[Sequence[Parameter]] | None = None,
        **kwargs: Any,
    ) -> RuntimeJob:
        """Submit a request to the estimator primitive program.

        Args:
            circuits: a (parameterized) :class:`~qiskit.circuit.QuantumCircuit` or
                a list of (parameterized) :class:`~qiskit.circuit.QuantumCircuit`.

            observables: A list of observable objects.

            parameter_values: An optional list of concrete parameters to be bound.

            parameters: A list of parameters of the quantum circuits
                (:class:`~qiskit.circuit.parametertable.ParameterView` or
                a list of :class:`~qiskit.circuit.Parameter`).
                Defaults to ``[circ.parameters for circ in circuits]``.

            **kwargs: Individual options to overwrite the default primitive options.

        Returns:
            Submitted job.

        Raises:
            ValueError: If the input values are invalid.
        """
        if isinstance(circuits, Iterable) and not all(
            isinstance(inst, QuantumCircuit) for inst in circuits
        ):
            raise ValueError(
                "The circuits parameter has to be instances of QuantumCircuit."
            )

        circ_count = 1 if isinstance(circuits, QuantumCircuit) else len(circuits)
        obs_count = (
            1
            if isinstance(observables, (BaseOperator, PauliSumOp))
            else len(observables)
        )

        inputs = {
            "circuits": circuits,
            "circuit_indices": list(range(circ_count)),
            "observables": observables,
            "observable_indices": list(range(obs_count)),
            "parameters": parameters,
            "parameter_values": parameter_values,
        }

        combined = self.options._merge_options(kwargs)
        inputs.update(Options._get_program_inputs(combined))

        return self._session.run(
            program_id=self._PROGRAM_ID,
            inputs=inputs,
            options=Options._get_runtime_options(combined),
            result_decoder=EstimatorResultDecoder,
        )

    def __call__(
        self,
        circuits: Sequence[int],
        observables: Sequence[int],
        parameter_values: Optional[
            Union[Sequence[float], Sequence[Sequence[float]]]
        ] = None,
        **run_options: Any,
    ) -> EstimatorResult:
        issue_deprecation_msg(
            msg="Calling an Estimator instance directly has been deprecated ",
            version="0.7",
            remedy="Please use qiskit_ibm_runtime.Session and Estimator.run() instead.",
        )
        return super().__call__(circuits, observables, parameter_values, **run_options)

    def _call(
        self,
        circuits: Sequence[int],
        observables: Sequence[int],
        parameter_values: Optional[
            Union[Sequence[float], Sequence[Sequence[float]]]
        ] = None,
        **run_options: Any,
    ) -> EstimatorResult:
        """Estimates expectation values for given inputs in a runtime session.

        Args:
            circuits: A list of circuit indices.
            observables: A list of observable indices.
            parameter_values: An optional list of concrete parameters to be bound.
            **run_options: A collection of kwargs passed to `backend.run()`.

                shots: Number of repetitions of each circuit, for sampling.
                qubit_lo_freq: List of default qubit LO frequencies in Hz.
                meas_lo_freq: List of default measurement LO frequencies in Hz.
                schedule_los: Experiment LO configurations, frequencies are given in Hz.
                rep_delay: Delay between programs in seconds. Only supported on certain
                    backends (if ``backend.configuration().dynamic_reprate_enabled=True``).
                init_qubits: Whether to reset the qubits to the ground state for each shot.
                use_measure_esp: Whether to use excited state promoted (ESP) readout for measurements
                    which are the terminal instruction to a qubit. ESP readout can offer higher fidelity
                    than standard measurement sequences.

        Returns:
            An instance of :class:`qiskit.primitives.EstimatorResult`.
        """
        inputs = {
            "circuits": self._initial_inputs["circuits"],
            "parameters": self._initial_inputs["parameters"],
            "observables": self._initial_inputs["observables"],
            "circuit_indices": circuits,
            "parameter_values": parameter_values,
            "observable_indices": observables,
        }
        combined = self.options._merge_options(run_options)
        inputs.update(Options._get_program_inputs(combined))

        return self._session.run(
            program_id=self._PROGRAM_ID,
            inputs=inputs,
            options=Options._get_runtime_options(combined),
            result_decoder=EstimatorResultDecoder,
        ).result()

    def close(self) -> None:
        """Close the session and free resources"""
        self._session.close()

    @property
    def session(self) -> Session:
        """Return session used by this primitive.

        Returns:
            Session used by this primitive.
        """
        return self._session


class EstimatorResultDecoder(ResultDecoder):
    """Class used to decode estimator results"""

    @classmethod
    def decode(cls, raw_result: str) -> EstimatorResult:
        """Convert the result to EstimatorResult."""
        decoded: Dict = super().decode(raw_result)
        return EstimatorResult(
            values=np.asarray(decoded["values"]),
            metadata=decoded["metadata"],
        )
