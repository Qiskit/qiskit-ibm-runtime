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
import copy

from qiskit.circuit import QuantumCircuit, Parameter

# pylint: disable=unused-import,cyclic-import
# from qiskit_ibm_runtime import session as new_session
from qiskit_ibm_runtime import Session

# TODO import BaseSampler and SamplerResult from terra once released
from .qiskit.primitives import BaseSampler, SamplerResult
from .qiskit_runtime_service import QiskitRuntimeService
from .options import Options
from .runtime_options import RuntimeOptions
from .program.result_decoder import ResultDecoder
from .runtime_session import RuntimeSession
from .runtime_job import RuntimeJob
from .utils.deprecation import deprecate_arguments, issue_deprecation_msg
from qiskit_ibm_runtime import _default_session


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
            settings = Sampler.default_settings()
            settings.service_options.backend = "ibmq_qasm_simulator"
            settings.transpilation.optimization_level = 1

            sampler = session.sampler(settings)
            job1 = sampler.run(bell)
            print(f"Bell job ID: {job1.job_id}")
            print(f"Bell result: {job1.result()}")

            settings.transpilation.optimization_level = 3
            job2 = sampler.run(
                circuits=[pqc, pqc, pqc2],
                parameter_values=[theta1, theta2, theta3],
                settings=settings)
            print(f"RealAmplitudes job ID: {job2.job_id}")
            print(f"RealAmplitudes result: {job2.result()}")
    """

    _PROGRAM_ID = "sampler"

    def __init__(
        self,
        circuits: Optional[Union[QuantumCircuit, Iterable[QuantumCircuit]]] = None,
        parameters: Optional[Iterable[Iterable[Parameter]]] = None,
        service: Optional[QiskitRuntimeService] = None,
        session: Optional[Session] = None,
        options: Optional[Union[Dict, RuntimeOptions, Options]] = None,
        skip_transpilation: Optional[bool] = False,
    ):
        """Initializes the Sampler primitive.

        Args:
            circuits: (DEPRECATED) A (parameterized) :class:`~qiskit.circuit.QuantumCircuit` or
                a list of (parameterized) :class:`~qiskit.circuit.QuantumCircuit`.

            parameters: (DEPRECATED) A list of parameters of the quantum circuits
                (:class:`~qiskit.circuit.parametertable.ParameterView` or
                a list of :class:`~qiskit.circuit.Parameter`)

            service: (DEPRECATED) Optional instance of
                :class:`qiskit_ibm_runtime.QiskitRuntimeService` class,
                defaults to `QiskitRuntimeService()` which tries to initialize your default
                saved account.

            session: Session in which to call the sampler primitive. If ``None``, a new session
                is created using the default saved account.

            options: Primitive options, see :class:`Options` for detailed description.

            skip_transpilation (DEPRECATED): Transpilation is skipped if set to True. False by default.
                Ignored ``skip_transpilation`` is also specified in ``options``.
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
        if service:
            deprecate_arguments(
                "service",
                "0.7",
                "Please use the session parameter instead."
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
            skip_transpilation = options.get("transpilation", {}).get("skip_transpilation", False)

        self.options.transpilation.skip_transpilation = skip_transpilation

        self._session: Union[Session, RuntimeSession] = None
        self._initial_inputs = {
            "circuits": circuits,
            "parameters": parameters
        }
        if session:
            self._session = session
        else:
            if _default_session is None:
                _default_session = Session(service=service)
            self._session = Session(service=service)


    def run(
        self,
        circuits: Union[QuantumCircuit, Sequence[QuantumCircuit]],
        parameter_values: Sequence[Sequence[float]] | None = None,
        parameters: Sequence[Sequence[Parameter]] | None = None,
        options: Optional[Dict | Options] = None,
        **run_options,
    ) -> RuntimeJob:
        """Submit a request to the sampler primitive program.

        Args:
            circuits: A (parameterized) :class:`~qiskit.circuit.QuantumCircuit` or
                a list of (parameterized) :class:`~qiskit.circuit.QuantumCircuit`.

            parameter_values: An optional list of concrete parameters to be bound.

            parameters: A list of parameters of the quantum circuits
                (:class:`~qiskit.circuit.parametertable.ParameterView` or
                a list of :class:`~qiskit.circuit.Parameter`).
                Defaults to ``[circ.parameters for circ in circuits]``.

            options: Options used for this execution only. It doesn't change the options
                for this primitive.

            run_options: Individual options to overwrite the default primitive options or
                values specified in ``options``.

        Returns:
            Submitted job.

        Raises:
            ValueError: If the input values are invalid.
        """
        # TODO: Something about run_options
        
        if isinstance(circuits, Iterable) and not all(
            isinstance(inst, QuantumCircuit) for inst in circuits
        ):
            raise ValueError(
                "The circuits parameter has to be instances of QuantumCircuit."
            )

        circ_count = 1 if isinstance(circuits, QuantumCircuit) else len(circuits)

        inputs = {
            "circuits": circuits,
            "parameters": parameters,
            "circuit_indices": list(range(circ_count)),
            "parameter_values": parameter_values,
        }
        options = options or self.options
        inputs.update(options._to_program_inputs())

        return self._session.run(
            program_id=self._PROGRAM_ID,
            inputs=inputs,
            options=options._to_runtime_options(),
            result_decoder=SamplerResultDecoder,
        )

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

        inputs = {
            "circuits": self._initial_inputs["circuits"],
            "parameters": self._initial_inputs["parameters"],
            "circuit_indices": circuits,
            "parameter_values": parameter_values,
        }
        inputs.update(self.options._to_program_inputs(run_options=run_options))

        return self._session.run(
            program_id=self._PROGRAM_ID,
            inputs=inputs,
            options=self.options._to_runtime_options(),
            result_decoder=SamplerResultDecoder,
        )

    def close(self) -> None:
        """Close the session and free resources"""
        self._session.close()

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
