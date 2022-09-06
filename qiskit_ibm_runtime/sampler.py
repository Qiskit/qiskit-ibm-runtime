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
from math import sqrt
from typing import Dict, Iterable, Optional, Sequence, Any, Union
import copy

from qiskit.circuit import QuantumCircuit, Parameter
from qiskit.circuit.parametertable import ParameterView
from qiskit.result import QuasiDistribution

# TODO import BaseSampler and SamplerResult from terra once released
from .qiskit.primitives import BaseSampler, SamplerResult
from .qiskit_runtime_service import QiskitRuntimeService
from .options import Options
from .program.result_decoder import ResultDecoder
from .runtime_job import RuntimeJob
from .ibm_backend import IBMBackend
from .session import get_default_session
from .utils.deprecation import deprecate_arguments, issue_deprecation_msg

# pylint: disable=unused-import,cyclic-import
from .session import Session


class Sampler(BaseSampler):
    """Class for interacting with Qiskit Runtime Sampler primitive service.

    Qiskit Runtime Sampler primitive service calculates probabilities or quasi-probabilities
    of bitstrings from quantum circuits.

    The :meth:`run` method can be used to submit circuits and parameters to the Sampler primitive.

    You are encourage to use :class:`~qiskit_ibm_runtime.Session` to open a session,
    during which you can invoke one or more primitive programs. Jobs sumitted within a session
    are prioritized by the scheduler, and data is cached for efficiency.

    Example::

        from qiskit.test.reference_circuits import ReferenceCircuits
        from qiskit_ibm_runtime import QiskitRuntimeService, Session, Sampler

        service = QiskitRuntimeService(channel="ibm_cloud")
        bell = ReferenceCircuits.bell()

        with Session(service) as session:
            sampler = Sampler(session=session)
            sampler.options.resilience_level = 1

            job = sampler.run(bell)
            print(f"Job ID: {job.job_id()}")
            print(f"Job result: {job.result()}")
    """

    _PROGRAM_ID = "sampler"

    def __init__(
        self,
        circuits: Optional[Union[QuantumCircuit, Iterable[QuantumCircuit]]] = None,
        parameters: Optional[Iterable[Iterable[Parameter]]] = None,
        service: Optional[QiskitRuntimeService] = None,
        session: Optional[Union[Session, str, IBMBackend]] = None,
        options: Optional[Union[Dict, Options]] = None,
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

            session: Session in which to call the primitive. If an instance of
                :class:`qiskit_ibm_runtime.IBMBackend` class or
                string name of a backend is specified, a new session is created for
                that backend. If ``None``, a new session is created using the default
                saved account and a default backend (IBM Cloud channel only).

            options: Primitive options, see :class:`Options` for detailed description.
                The ``backend`` keyword is still supported but is deprecated.

            skip_transpilation (DEPRECATED): Transpilation is skipped if set to True. False by default.
                Ignored ``skip_transpilation`` is also specified in ``options``.
        """
        super().__init__(
            circuits=circuits,
            parameters=parameters,
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

        backend = None
        self._session: Session = None

        if options is None:
            self.options = Options()
        elif isinstance(options, Options):
            self.options = copy.deepcopy(options)
            skip_transpilation = self.options.transpilation.skip_transpilation
        else:
            backend = options.pop("backend", None)
            if backend is not None:
                issue_deprecation_msg(
                    msg="The 'backend' key in 'options' has been deprecated",
                    version="0.7",
                    remedy="Please pass the backend when opening a session.",
                )
            self.options = Options._from_dict(options)
            skip_transpilation = options.get("transpilation", {}).get(
                "skip_transpilation", False
            )
        self.options.transpilation.skip_transpilation = skip_transpilation

        self._initial_inputs = {"circuits": circuits, "parameters": parameters}
        if isinstance(session, Session):
            self._session = session
        else:
            backend = session or backend
            self._session = get_default_session(service, backend)

    def run(
        self,
        circuits: QuantumCircuit | Sequence[QuantumCircuit],
        parameter_values: Sequence[float] | Sequence[Sequence[float]] | None = None,
        parameters: Sequence[Parameter] | Sequence[Sequence[Parameter]] | None = None,
        **kwargs: Any,
    ) -> RuntimeJob:
        """Submit a request to the sampler primitive program.

        Args:
            circuits: A (parameterized) :class:`~qiskit.circuit.QuantumCircuit` or
                a list of (parameterized) :class:`~qiskit.circuit.QuantumCircuit`.
            parameter_values: Concrete parameters to be bound.
            parameters: Parameters of each of the quantum circuits.
                Defaults to ``[circ.parameters for circ in circuits]``.
            **kwargs: Individual options to overwrite the default primitive options.

        Returns:
            Submitted job.

        Raises:
            QiskitError: Invalid arguments are given.
        """
        if not isinstance(circuits, Sequence):
            circuits = [circuits]
        if (
            parameter_values is not None
            and len(parameter_values) > 1
            and not isinstance(parameter_values[0], Sequence)
        ):
            parameter_values = [parameter_values]  # type: ignore[assignment]
        if (
            parameters is not None
            and len(parameters) > 1
            and not isinstance(parameters[0], Sequence)
        ):
            parameters = [parameters]

        return super().run(
            circuits=circuits,
            parameter_values=parameter_values,
            parameters=parameters,
            **kwargs,
        )

    def _run(
        self,
        circuits: Sequence[QuantumCircuit],
        parameter_values: Sequence[Sequence[float]],
        parameters: Sequence[ParameterView],
        **kwargs: Any,
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

            **kwargs: Individual options to overwrite the default primitive options.

        Returns:
            Submitted job.
        """
        inputs = {
            "circuits": circuits,
            "parameters": parameters,
            "circuit_indices": list(range(len(circuits))),
            "parameter_values": parameter_values,
        }
        combined = self.options._merge_options(kwargs)
        inputs.update(Options._get_program_inputs(combined))

        return self._session.run(
            program_id=self._PROGRAM_ID,
            inputs=inputs,
            options=Options._get_runtime_options(combined),
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
        combined = self.options._merge_options(run_options)
        inputs.update(Options._get_program_inputs(combined))

        raw_result = self._session.run(
            program_id=self._PROGRAM_ID,
            inputs=inputs,
            options=Options._get_runtime_options(combined),
            result_decoder=SamplerResultDecoder,
        ).result()
        quasi_dists = []
        for quasi, meta in zip(raw_result["quasi_dists"], raw_result["metadata"]):
            shots = meta.get("shots", float("inf"))
            overhead = meta.get("readout_mitigation_overhead", 1.0)

            # M3 mitigation overhead is gamma^2
            # https://github.com/Qiskit-Partners/mthree/blob/423d7e83a12491c59c9f58af46b75891bc622949/mthree/mitigation.py#L457
            #
            # QuasiDistribution stddev_upper_bound is gamma / sqrt(shots)
            # https://github.com/Qiskit/qiskit-terra/blob/ff267b5de8b83aef86e2c9ac6c7f918f58500505/qiskit/result/mitigation/local_readout_mitigator.py#L288
            stddev = sqrt(overhead / shots)
            quasi_dists.append(
                QuasiDistribution(quasi, shots=shots, stddev_upper_bound=stddev)
            )
        return SamplerResult(
            quasi_dists=quasi_dists,
            metadata=raw_result["metadata"],
        )

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
