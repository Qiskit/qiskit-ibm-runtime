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
import logging
from dataclasses import asdict

from qiskit.circuit import QuantumCircuit, Parameter
from qiskit.providers.options import Options as TerraOptions
from qiskit.primitives import BaseSampler, SamplerResult

# TODO import _circuit_key from terra once 0.23 released
from .qiskit_runtime_service import QiskitRuntimeService
from .options import Options
from .runtime_job import RuntimeJob
from .ibm_backend import IBMBackend
from .session import get_default_session
from .utils.deprecation import (
    deprecate_arguments,
    issue_deprecation_msg,
    deprecate_function,
)
from .constants import DEFAULT_DECODERS

# pylint: disable=unused-import,cyclic-import
from .session import Session

logger = logging.getLogger(__name__)


class Sampler(BaseSampler):
    """Class for interacting with Qiskit Runtime Sampler primitive service.

    Qiskit Runtime Sampler primitive service calculates probabilities or quasi-probabilities
    of bitstrings from quantum circuits.

    The :meth:`run` method can be used to submit circuits and parameters to the Sampler primitive.

    You are encouraged to use :class:`~qiskit_ibm_runtime.Session` to open a session,
    during which you can invoke one or more primitive programs. Jobs submitted within a session
    are prioritized by the scheduler, and data is cached for efficiency.

    Example::

        from qiskit.test.reference_circuits import ReferenceCircuits
        from qiskit_ibm_runtime import QiskitRuntimeService, Session, Sampler

        service = QiskitRuntimeService(channel="ibm_cloud")
        bell = ReferenceCircuits.bell()

        with Session(service, backend="ibmq_qasm_simulator") as session:
            sampler = Sampler(session=session)

            job = sampler.run(bell, shots=1024)
            print(f"Job ID: {job.job_id()}")
            print(f"Job result: {job.result()}")
            # Close the session only if all jobs are finished
            # and you don't need to run more in the session.
            session.close()
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

            session: Session in which to call the primitive.

                * If an instance of :class:`qiskit_ibm_runtime.IBMBackend` class or
                  string name of a backend is specified, a new session is created for
                  that backend, unless a default session for the same backend
                  and channel already exists.

                * If ``None``, a new session is created using the default saved
                  account and a default backend (IBM Cloud channel only), unless
                  a default session already exists.

            options: Primitive options, see :class:`Options` for detailed description.
                The ``backend`` keyword is still supported but is deprecated.

            skip_transpilation (DEPRECATED): Transpilation is skipped if set to True. False by default.
                Ignored if ``skip_transpilation`` is also specified in ``options``.
        """
        # `_options` in this class is an instance of qiskit_ibm_runtime.Options class.
        # The base class, however, uses a `_run_options` which is an instance of
        # qiskit.providers.Options. We largely ignore this _run_options because we use
        # a nested dictionary to categorize options.

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
            _options = Options()
        elif isinstance(options, Options):
            _options = copy.deepcopy(options)
            skip_transpilation = (
                _options.transpilation.skip_transpilation  # type: ignore[union-attr]
            )
        else:
            options_copy = copy.deepcopy(options)
            backend = options_copy.pop("backend", None)
            if backend is not None:
                issue_deprecation_msg(
                    msg="The 'backend' key in 'options' has been deprecated",
                    version="0.7",
                    remedy="Please pass the backend when opening a session.",
                )
            skip_transpilation = options.get("transpilation", {}).get(
                "skip_transpilation", False
            )
            log_level = options_copy.pop("log_level", None)
            _options = Options(**options_copy)
            if log_level:
                issue_deprecation_msg(
                    msg="The 'log_level' option has been moved to the 'environment' category",
                    version="0.7",
                    remedy="Please specify 'environment':{'log_level': log_level} instead.",
                )
                _options.environment.log_level = log_level  # type: ignore[union-attr]

        _options.transpilation.skip_transpilation = (  # type: ignore[union-attr]
            skip_transpilation
        )

        if _options.optimization_level is None:
            if _options.simulator and (
                not hasattr(_options.simulator, "noise_model")
                or asdict(_options.simulator)["noise_model"] is None
            ):
                _options.optimization_level = 1
            else:
                _options.optimization_level = Options._DEFAULT_OPTIMIZATION_LEVEL

        if _options.resilience_level is None:
            if _options.simulator and (
                not hasattr(_options.simulator, "noise_model")
                or asdict(_options.simulator)["noise_model"] is None
            ):
                _options.resilience_level = 0
            else:
                _options.resilience_level = Options._DEFAULT_RESILIENCE_LEVEL

        self._options: dict = asdict(_options)

        self._initial_inputs = {"circuits": circuits, "parameters": parameters}
        if isinstance(session, Session):
            self._session = session
        else:
            backend = session or backend
            self._session = get_default_session(service, backend)

        # self._first_run = True
        # self._circuits_map = {}
        # if self.circuits:
        #     for circuit in self.circuits:
        #         circuit_id = _hash(
        #             json.dumps(_circuit_key(circuit), cls=RuntimeEncoder)
        #         )
        #         if circuit_id not in self._session._circuits_map:
        #             self._circuits_map[circuit_id] = circuit
        #             self._session._circuits_map[circuit_id] = circuit

    def run(  # pylint: disable=arguments-differ
        self,
        circuits: QuantumCircuit | Sequence[QuantumCircuit],
        parameter_values: Sequence[float] | Sequence[Sequence[float]] | None = None,
        **kwargs: Any,
    ) -> RuntimeJob:
        """Submit a request to the sampler primitive program.

        Args:
            circuits: A (parameterized) :class:`~qiskit.circuit.QuantumCircuit` or
                a list of (parameterized) :class:`~qiskit.circuit.QuantumCircuit`.
            parameter_values: Concrete parameters to be bound.
            **kwargs: Individual options to overwrite the default primitive options.
                These include the runtime options in :class:`qiskit_ibm_runtime.RuntimeOptions`.

        Returns:
            Submitted job.
            The result of the job is an instance of :class:`qiskit.primitives.SamplerResult`.

        Raises:
            ValueError: Invalid arguments are given.
        """
        # To bypass base class merging of options.
        user_kwargs = {"_user_kwargs": kwargs}
        return super().run(
            circuits=circuits,
            parameter_values=parameter_values,
            **user_kwargs,
        )

    def _run(  # pylint: disable=arguments-differ
        self,
        circuits: Sequence[QuantumCircuit],
        parameter_values: Sequence[Sequence[float]],
        **kwargs: Any,
    ) -> RuntimeJob:
        """Submit a request to the sampler primitive program.

        Args:
            circuits: A (parameterized) :class:`~qiskit.circuit.QuantumCircuit` or
                a list of (parameterized) :class:`~qiskit.circuit.QuantumCircuit`.
            parameter_values: An optional list of concrete parameters to be bound.
            **kwargs: Individual options to overwrite the default primitive options.
                These include the runtime options in :class:`qiskit_ibm_runtime.RuntimeOptions`.

        Returns:
            Submitted job.
        """
        # TODO: Re-enable data caching when ntc 1748 is fixed
        # circuits_map = {}
        # circuit_ids = []
        # for circuit in circuits:
        #     circuit_id = _hash(json.dumps(_circuit_key(circuit), cls=RuntimeEncoder))
        #     circuit_ids.append(circuit_id)
        #     if circuit_id in self._session._circuits_map:
        #         continue
        #     self._session._circuits_map[circuit_id] = circuit
        #     circuits_map[circuit_id] = circuit

        # if self._first_run:
        #     self._first_run = False
        #     circuits_map.update(self._circuits_map)

        # inputs = {
        #     "circuits": circuits_map,
        #     "circuit_ids": circuit_ids,
        #     "parameter_values": parameter_values,
        # }
        inputs = {
            "circuits": circuits,
            "parameters": [circ.parameters for circ in circuits],
            "circuit_indices": list(range(len(circuits))),
            "parameter_values": parameter_values,
        }
        combined = Options._merge_options(self._options, kwargs.get("_user_kwargs", {}))
        logger.info("Submitting job using options %s", combined)
        inputs.update(Options._get_program_inputs(combined))

        return self._session.run(
            program_id=self._PROGRAM_ID,
            inputs=inputs,
            options=Options._get_runtime_options(combined),
            callback=combined.get("environment", {}).get("callback", None),
            result_decoder=DEFAULT_DECODERS.get(self._PROGRAM_ID),
        )

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
        combined = Options._merge_options(self._options, run_options)

        inputs.update(Options._get_program_inputs(combined))

        raw_result = self._session.run(
            program_id=self._PROGRAM_ID,
            inputs=inputs,
            options=Options._get_runtime_options(combined),
        ).result()

        return raw_result

    @deprecate_function(
        deprecated="close",
        version="0.7",
        remedy="Use qiskit_ibm_runtime.Session.close() instead",
    )
    def close(self) -> None:
        """Close the session and free resources.
        Close the session only if all jobs are finished and you don't need to run more in the session."""
        self._session.close()

    @property
    def session(self) -> Session:
        """Return session used by this primitive.

        Returns:
            Session used by this primitive.
        """
        return self._session

    @property
    def options(self) -> TerraOptions:
        """Return options values for the sampler.

        Returns:
            options
        """
        return TerraOptions(**self._options)

    def set_options(self, **fields: Any) -> None:
        """Set options values for the sampler.

        Args:
            **fields: The fields to update the options
        """
        self._options = Options._merge_options(self._options, fields)
