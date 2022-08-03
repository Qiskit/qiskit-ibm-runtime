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

"""Sampler primitive."""

from __future__ import annotations
from typing import Dict, Iterable, Optional, Sequence, Any, Union
from dataclasses import dataclass, asdict

from qiskit.circuit import QuantumCircuit, Parameter

# pylint: disable=unused-import,cyclic-import
from qiskit_ibm_runtime import session as new_session

# TODO import BaseSampler and SamplerResult from terra once released
from .qiskit.primitives import BaseSampler, SamplerResult
from .qiskit_runtime_service import QiskitRuntimeService
from .settings import Transpilation, Resilience
from .runtime_options import RuntimeOptions
from .program.result_decoder import ResultDecoder
from .runtime_session import RuntimeSession
from .runtime_job import RuntimeJob
from .utils.deprecation import deprecate_arguments, issue_deprecation_msg


class Sampler(BaseSampler):
    """Class for interacting with Qiskit Runtime Sampler primitive service.

    Qiskit Runtime Sampler primitive service calculates probabilities or quasi-probabilities
    of bitstrings from quantum circuits.

    The :meth:`run` method can be used to submit circuits and parameters to the Sampler primitive.

    You are encourage to use :class:`~qiskit_ibm_runtime.Session` to open a session,
    during which you can invoke one or more primitive programs. Jobs sumitted within a session
    are prioritized by the scheduler, and data is cached for efficiency.

    Example::

        from qiskit import QuantumCircuit
        from qiskit.circuit.library import RealAmplitudes

        from qiskit_ibm_runtime import QiskitRuntimeService, Session

        service = QiskitRuntimeService(channel="ibm_cloud")

        # Bell circuit
        bell = QuantumCircuit(2)
        bell.h(0)
        bell.cx(0, 1)
        bell.measure_all()

        # parameterized circuit
        pqc = RealAmplitudes(num_qubits=2, reps=2)
        pqc.measure_all()
        pqc2 = RealAmplitudes(num_qubits=2, reps=3)
        pqc2.measure_all()

        theta1 = [0, 1, 1, 2, 3, 5]
        theta2 = [1, 2, 3, 4, 5, 6]
        theta3 = [0, 1, 2, 3, 4, 5, 6, 7]

        with Session(service) as session:
            sampler = session.sampler()
            sampler.options.backend = "ibmq_qasm_simulator"
            sampler.settings.transpilation.optimization_level = 1
            job1 = sampler.run(bell)
            print(f"Bell job ID: {job1.job_id}")
            print(f"Bell result:" {job1.result()})

            job2 = sampler.run(circuits=[pqc, pqc2], parameter_values=[theta1, theta2, theta3])
            print(f"RealAmplitudes job ID: {job2.job_id}")
            print(f"RealAmplitudes result:" {job2.result()})
    """

    _PROGRAM_ID = "sampler"

    def __init__(
        self,
        circuits: Optional[Union[QuantumCircuit, Iterable[QuantumCircuit]]] = None,
        parameters: Optional[Iterable[Iterable[Parameter]]] = None,
        service: Optional[QiskitRuntimeService] = None,
        options: Optional[Union[Dict, RuntimeOptions]] = None,
        skip_transpilation: Optional[bool] = False,
        transpilation_settings: Optional[Union[Dict, Transpilation]] = None,
        resilience_settings: Optional[Union[Dict, Resilience]] = None,
        session: Optional["new_session.Session"] = None,
    ):
        """Initializes the Sampler primitive.

        Args:
            circuits: (DEPRECATED) A (parameterized) :class:`~qiskit.circuit.QuantumCircuit` or
                a list of (parameterized) :class:`~qiskit.circuit.QuantumCircuit`.

            parameters: (DEPRECATED) A list of parameters of the quantum circuits
                (:class:`~qiskit.circuit.parametertable.ParameterView` or
                a list of :class:`~qiskit.circuit.Parameter`)

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

            skip_transpilation (DEPRECATED): Transpilation is skipped if set to True. False by default.
                Ignored if ``skip_transpilation`` is also specified in ``transpilation_settings``.

            transpilation_settings: (EXPERIMENTAL setting, can break between releases without warning)
                Qiskit transpiler settings. The transpilation process converts
                operations in the circuit to those supported by the backend, swaps qubits with the
                circuit to overcome limited qubit connectivity and some optimizations to reduce the
                circuit's gate count where it can.

                * skip_transpilation: Transpilation is skipped if set to True.
                    False by default.

                * optimization_level: How much optimization to perform on the circuits.
                    Higher levels generate more optimized circuits,
                    at the expense of longer transpilation times.

                    * 0: no optimization
                    * 1: light optimization (default)
                    * 2: heavy optimization
                    * 3: even heavier optimization

            resilience_settings: (EXPERIMENTAL setting, can break between releases without warning)
                Using these settings allows you to build resilient algorithms by
                leveraging the state of the art error suppression, mitigation and correction techniques.

                * level: How much resilience to build against errors.
                    Higher levels generate more accurate results,
                    at the expense of longer processing times.
                    * 0: no resilience
                    * 1: light resilience
                    If ``None``, level 0 will be chosen as default.

            session: Session in which to call the sampler primitive.
        """
        # TODO: Fix base classes once done
        super().__init__(
            circuits=circuits,
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
            transpilation_settings = Transpilation(
                skip_transpilation=skip_transp, **transpilation_settings
            )
        resilience_settings = resilience_settings or {}
        if isinstance(resilience_settings, Dict):
            resilience_settings = Resilience(**resilience_settings)

        self.settings = SamplerSettings(
            transpilation=transpilation_settings, resilience=resilience_settings
        )
        options = options or {}
        # TODO: Having options and run_options is very confusing. Can we combine the two?
        if not isinstance(options, RuntimeOptions):
            options = RuntimeOptions(**options)
        self.options = options

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
                "parameters": parameters,
            }
            inputs.update(self._to_program_settings())

            # Cannot use the new Session or will get circular import.
            self._session = RuntimeSession(
                service=service,
                program_id=self._PROGRAM_ID,
                inputs=inputs,
                options=asdict(self.options),
            )

    def run(
        self,
        circuits: Union[QuantumCircuit, Iterable[QuantumCircuit]],
        parameters: Optional[Iterable[Iterable[Parameter]]] = None,
        parameter_values: Optional[
            Union[Sequence[float], Sequence[Sequence[float]]]
        ] = None,
        **run_options: Any,
    ) -> RuntimeJob:
        """Submit a request to the sampler primitive program.

        Args:
            circuits: A (parameterized) :class:`~qiskit.circuit.QuantumCircuit` or
                a list of (parameterized) :class:`~qiskit.circuit.QuantumCircuit`.

            parameters: A list of parameters of the quantum circuits
                (:class:`~qiskit.circuit.parametertable.ParameterView` or
                a list of :class:`~qiskit.circuit.Parameter`).
                Defaults to ``[circ.parameters for circ in circuits]``.

            parameter_values: An optional list of concrete parameters to be bound.

            **run_options: A collection of kwargs passed to `backend.run()`.

                * shots: Number of repetitions of each circuit, for sampling.
                * qubit_lo_freq: List of default qubit LO frequencies in Hz.
                * meas_lo_freq: List of default measurement LO frequencies in Hz.
                * schedule_los: Experiment LO configurations, frequencies are given in Hz.
                * rep_delay: Delay between programs in seconds. Only supported on certain
                    backends (if ``backend.configuration().dynamic_reprate_enabled=True``).
                * init_qubits: Whether to reset the qubits to the ground state for each shot.
                * use_measure_esp: Whether to use excited state promoted (ESP) readout for measurements
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
                "(e.g. when Sampler is used as a context manager). Please use "
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
        elif hasattr(circuits, "__len__"):
            circ_count = len(circuits)  # type: ignore[arg-type]
        else:
            circ_count = sum(1 for _ in circuits)
        circuit_indices = list(range(circ_count))

        inputs = {
            "circuits": circuits,
            "parameters": parameters,
            "circuit_indices": circuit_indices,
            "parameter_values": parameter_values,
            "run_options": run_options,
        }
        inputs.update(self._to_program_settings())

        return self._session.run(
            program_id=self._PROGRAM_ID,
            inputs=inputs,
            options=self.options,
            result_decoder=SamplerResultDecoder,
        )

    def _to_program_settings(self) -> Dict:
        """Convert SamplerSettings to primitive program format.

        Returns:
            Settings in the format expected by the primitive program.
        """
        # TODO: Remove this once primitive program is updated to use optimization_level.
        transpilation_settings = asdict(self.settings.transpilation)
        transpilation_settings["optimization_settings"] = {
            "level": transpilation_settings["optimization_level"]
        }
        return {
            "resilience_settings": asdict(self.settings.resilience),
            "transpilation_settings": transpilation_settings,
        }

    def __call__(
        self,
        circuits: Sequence[int | QuantumCircuit],
        parameter_values: Sequence[Sequence[float]] | None = None,
        **run_options: Any,
    ) -> SamplerResult:
        issue_deprecation_msg(
            msg="Calling a Sampler instance directly has been deprecated ",
            version="0.7",
            remedy="Please use qiskit_ibm_runtime.Session and Sampler.run() instead.",
        )

        if not isinstance(self._session, RuntimeSession):
            raise ValueError(
                "The run method is only supported when "
                "qiskit_ibm_runtime.RuntimeSession is used ",
                "(e.g. when Sampler is used as a context manager).",
            )
        return super().__call__(circuits, parameter_values, **run_options)

    def _call(
        self,
        circuits: Sequence[int],
        parameter_values: Optional[
            Union[Sequence[float], Sequence[Sequence[float]]]
        ] = None,
        **run_options: Any,
    ) -> SamplerResult:
        """Calculates probabilities or quasi-probabilities for given inputs in a runtime session.

        Args:
            circuits: A list of circuit indices.
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
            An instance of :class:`qiskit.primitives.SamplerResult`.
        """

        self._session.write(  # type: ignore[union-attr]
            circuit_indices=circuits,
            parameter_values=parameter_values,
            run_options=run_options,
        )
        raw_result = self._session.read()  # type: ignore[union-attr]
        return SamplerResult(
            quasi_dists=raw_result["quasi_dists"],
            metadata=raw_result["metadata"],
        )

    def close(self) -> None:
        """Close the session and free resources"""
        self._session.close()

    @classmethod
    def default_settings(cls) -> SamplerSettings:
        """Return the default settings.

        Returns:
            Default Sampler settings.
        """
        return SamplerSettings()


@dataclass
class SamplerSettings:
    """Sampler settings."""

    transpilation: Transpilation = Transpilation()
    resilience: Resilience = Resilience()


class SamplerResultDecoder(ResultDecoder):
    """Class used to decode sampler results."""

    @classmethod
    def decode(cls, raw_result: str) -> SamplerResult:
        """Convert the result to SamplerResult."""
        decoded: Dict = super().decode(raw_result)
        return SamplerResult(
            quasi_dists=decoded["quasi_dists"],
            metadata=decoded["metadata"],
        )
