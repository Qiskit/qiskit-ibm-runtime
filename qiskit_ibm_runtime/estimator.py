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

from dataclasses import asdict
from typing import Iterable, Optional, Dict, Sequence, Any, Union

from qiskit.circuit import QuantumCircuit, Parameter
from qiskit.quantum_info import SparsePauliOp

# pylint: disable=unused-import,cyclic-import
from qiskit_ibm_runtime import session as new_session

# TODO import BaseEstimator and EstimatorResult from terra once released
from .qiskit.primitives import BaseEstimator, EstimatorResult
from .exceptions import IBMInputValueError
from .ibm_backend import IBMBackend
from .qiskit_runtime_service import QiskitRuntimeService
from .runtime_session import RuntimeSession
from .program.result_decoder import ResultDecoder
from .runtime_job import RuntimeJob
from .utils.deprecation import deprecate_arguments, issue_deprecation_msg
from .runtime_options import RuntimeOptions
from .settings import Transpilation, Resilience


class Estimator(BaseEstimator):
    """Class for interacting with Qiskit Runtime Estimator primitive service.

    Qiskit Runtime Estimator primitive service estimates expectation values of quantum circuits and
    observables.

    The :meth: `run` can be used to submit circuits, observables, and parameters
    to the Estimator primitive.

    You are encouraged to use :class:`~qiskit_ibm_runtime.Session` to open a session,
    during which you can invoke one or more primitive programs. Jobs submitted within a session
    are prioritized by the scheduler, and data is cached for efficiency.

    Example::

        from qiskit.circuit.library import RealAmplitudes
        from qiskit.quantum_info import SparsePauliOp

        from qiskit_ibm_runtime import QiskitRuntimeService, Estimator

        service = QiskitRuntimeService(channel="ibm_cloud")
        options = { "backend": "ibmq_qasm_simulator" }

        psi1 = RealAmplitudes(num_qubits=2, reps=2)
        psi2 = RealAmplitudes(num_qubits=2, reps=3)

        H1 = SparsePauliOp.from_list([("II", 1), ("IZ", 2), ("XI", 3)])
        H2 = SparsePauliOp.from_list([("IZ", 1)])
        H3 = SparsePauliOp.from_list([("ZI", 1), ("ZZ", 1)])

        with Session(service) as session:
            estimator = session.estimator()
            estimator.options.backend = 'ibmq_qasm_simulator'
            estimator.settings.transpilation.optimization_level = 1

            theta1 = [0, 1, 1, 2, 3, 5]
            theta2 = [0, 1, 1, 2, 3, 5, 8, 13]
            theta3 = [1, 2, 3, 4, 5, 6]

            # calculate [ <psi1(theta1)|H1|psi1(theta1)> ]
            # pass circuits and observables as indices
            psi1_H1 = estimator.run(psi1, H1, theta1)
            print(psi1_H1.result())

            # calculate [ <psi1(theta1)|H2|psi1(theta1)>, <psi1(theta1)|H3|psi1(theta1)> ]
            # alternatively you can also pass circuits and observables as objects
            psi1_H23 = estimator.run([psi1, psi1], [H2, H3], [theta1]*2)
            print(psi1_H23.result())

            # calculate [ <psi2(theta2)|H2|psi2(theta2)> ]
            psi2_H2 = estimator.run([psi2], [H2], [theta2])
            print(psi2_H2.result())

            # calculate [ <psi1(theta1)|H1|psi1(theta1)>, <psi1(theta3)|H1|psi1(theta3)> ]
            psi1_H1_job = estimator.run([psi1, psi1], [H1, H1], [theta1, theta3])
            print(psi1_H1_job.result())

            # calculate [ <psi1(theta1)|H1|psi1(theta1)>,
            #             <psi2(theta2)|H2|psi2(theta2)>,
            #             <psi1(theta3)|H3|psi1(theta3)> ]
            psi12_H23 = estimator.run([psi1, psi2, psi1], [H1, H2, H3], [theta1, theta2, theta3])
            print(psi12_H23.result())
    """

    _PROGRAM_ID = "estimator"

    def __init__(
        self,
        circuits: Optional[Union[QuantumCircuit, Iterable[QuantumCircuit]]] = None,
        observables: Optional[Iterable[SparsePauliOp]] = None,
        parameters: Optional[Iterable[Iterable[Parameter]]] = None,
        service: Optional[QiskitRuntimeService] = None,
        options: Optional[Union[Dict, RuntimeOptions]] = None,
        skip_transpilation: Optional[bool] = False,
        transpilation_settings: Optional[Dict] = None,
        resilience_settings: Optional[Dict] = None,
        session: Optional["new_session.Session"] = None,
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

            service: Optional instance of :class:`qiskit_ibm_runtime.QiskitRuntimeService` class,
                defaults to `QiskitRuntimeService()` which tries to initialize your default
                saved account.

            options: Runtime options dictionary that control the execution environment.

                * backend: Optional instance of :class:`qiskit_ibm_runtime.IBMBackend` class or
                    string name of backend, if not specified a backend will be selected
                    automatically (IBM Cloud only).
                * image: the runtime image used to execute the program, specified in
                    the form of ``image_name:tag``. Not all accounts are
                    authorized to select a different image.
                * log_level: logging level to set in the execution environment. The valid
                    log levels are: ``DEBUG``, ``INFO``, ``WARNING``, ``ERROR``, and ``CRITICAL``.
                    The default level is ``WARNING``.

            skip_transpilation: (DEPRECATED) Transpilation is skipped if set to True. False by default.

            transpilation_settings: (EXPERIMENTAL setting, can break between releases without warning)
                Qiskit transpiler settings. The transpilation process converts
                operations in the circuit to those supported by the backend, swaps qubits with the
                circuit to overcome limited qubit connectivity and some optimizations to reduce the
                circuit's gate count where it can.

                * skip_transpilation: Transpilation is skipped if set to True.
                    False by default.

                * optimization_settings:

                    * level: How much optimization to perform on the circuits.
                        Higher levels generate more optimized circuits,
                        at the expense of longer transpilation times.
                        * 0: no optimization
                        * 1: light optimization
                        * 2: heavy optimization
                        * 3: even heavier optimization
                        If ``None``, level 1 will be chosen as default.

            resilience_settings: (EXPERIMENTAL setting, can break between releases without warning)
                Using these settings allows you to build resilient algorithms by
                leveraging the state of the art error suppression, mitigation and correction techniques.

                * level: How much resilience to build against errors.
                    Higher levels generate more accurate results,
                    at the expense of longer processing times.
                    * 0: no resilience
                    * 1: light resilience
                    If ``None``, level 0 will be chosen as default.

            session: Session in which to call the estimator primitive.
        """
        super().__init__(
            circuits=circuits,
            observables=observables,
            parameters=parameters,
        )

        # TODO: Remove deprecation warnings if done in base class
        if circuits or parameters:
            deprecate_arguments(
                "circuits and parameters",
                "0.7",
                f"You can instead specify these inputs using the {self.__class__.__name__}.run method.",
            )
        if skip_transpilation:
            deprecate_arguments(
                "skip_transpilation",
                "0.7",
                "Instead, use the skip_transpilation keyword argument in transpilation_settings.",
            )

        transpilation_settings = transpilation_settings or {}
        if isinstance(transpilation_settings, Dict):
            skip_transp = transpilation_settings.pop(
                "skip_transpilation", skip_transpilation
            )
            self._transpilation_settings = Transpilation(
                skip_transpilation=skip_transp, **transpilation_settings
            )
        resilience_settings = resilience_settings or {}
        if isinstance(resilience_settings, Dict):
            self._resilience_settings = Resilience(**resilience_settings)

        options = options or {}
        if not isinstance(options, RuntimeOptions):
            options = RuntimeOptions(**options)
        self._options = options

        self._session: Union[new_session.Session, RuntimeSession] = None
        if session:
            self._session = session
        else:
            # Backward compatibility mode
            if not service:
                # try to initialize service with default saved account
                service = QiskitRuntimeService()

            inputs = {
                "circuits": circuits,
                "observables": observables,
                "parameters": parameters,
            }
            inputs.update(self._get_settings())

            # Cannot use the new Session or will get circular import.
            self._session = RuntimeSession(
                service=service,
                program_id=self._PROGRAM_ID,
                inputs=inputs,
                options=self._options,
            )

    def run(
        self,
        circuits: Union[QuantumCircuit, Iterable[QuantumCircuit]],
        observables: Iterable[Iterable[Parameter]],
        parameter_values: Optional[
            Union[Sequence[float], Sequence[Sequence[float]]]
        ] = None,
        **run_options: Any,
    ) -> RuntimeJob:
        """Submit a request to the estimator primitive program.

        Args:
            circuits: a (parameterized) :class:`~qiskit.circuit.QuantumCircuit` or
                a list of (parameterized) :class:`~qiskit.circuit.QuantumCircuit`.

            observables: a list of :class:`~qiskit.quantum_info.SparsePauliOp`

            parameters: a list of parameters of the quantum circuits.
                (:class:`~qiskit.circuit.parametertable.ParameterView` or
                a list of :class:`~qiskit.circuit.Parameter`) specifying the order
                in which parameter values will be bound.

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
            Submitted job.

        Raises:
            ValueError: If the input values are invalid.
        """
        if isinstance(self._session, RuntimeSession):
            raise ValueError(
                "The run method is not supported when "
                "qiskit_ibm_runtime.RuntimeSession is used ",
                "(e.g. when Estimator is used as a context manager). Please use "
                "qiskit_ibm_runtime.Session as a context manager instead.",
            )

        if isinstance(circuits, Iterable) and not all(
            isinstance(inst, QuantumCircuit) for inst in circuits
        ):
            raise ValueError(
                "The circuits parameter has to be instances of QuantumCircuit."
            )

        if not isinstance(circuits, Iterable):
            circ_count = 1
        else:
            circ_count = sum(1 for _ in circuits)
        circuit_indices = list(range(circ_count))

        obs_count = sum(1 for _ in observables)

        inputs = {
            "circuits": circuits,
            "circuit_indices": circuit_indices,
            "observables": observables,
            "observable_indices": list(range(obs_count)),
            "parameter_values": parameter_values,
            "run_options": run_options,
        }

        return self._session.run(
            program_id=self._PROGRAM_ID,
            inputs=inputs,
            options=self._options,
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

        if not isinstance(self._session, RuntimeSession):
            raise ValueError(
                "The run method is only supported when "
                "qiskit_ibm_runtime.RuntimeSession is used ",
                "(e.g. when Estimator is used as a context manager).",
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
        self._session.write(  # type: ignore[union-attr]
            circuit_indices=circuits,
            observable_indices=observables,
            parameter_values=parameter_values,
            run_options=run_options,
        )
        raw_result = self._session.read()  # type: ignore[union-attr]
        return EstimatorResult(
            values=raw_result["values"],
            metadata=raw_result["metadata"],
        )

    def _get_settings(self) -> Dict:
        """Convert transpilation and resilience settings to a dictionary.

        Returns:
            Settings in the format expected by the primitive program.
        """
        transpilation_settings = asdict(self._transpilation_settings)
        transpilation_settings["optimization_settings"] = {
            "level": transpilation_settings["optimization_level"]
        }
        return {
            "resilience_settings": asdict(self._resilience_settings),
            "transpilation_settings": transpilation_settings,
        }

    def close(self) -> None:
        """Close the session and free resources"""
        self._session.close()


class EstimatorResultDecoder(ResultDecoder):
    """Class used to decode estimator results"""

    @classmethod
    def decode(cls, raw_result: str) -> EstimatorResult:
        """Convert the result to EstimatorResult."""
        decoded: Dict = super().decode(raw_result)
        return EstimatorResult(
            values=decoded["values"],
            metadata=decoded["metadata"],
        )
