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
import os
from typing import Dict, Optional, Sequence, Any, Union
import copy
import logging
from dataclasses import asdict

from qiskit.circuit import QuantumCircuit
from qiskit.providers.options import Options as TerraOptions
from qiskit.primitives import BaseSampler, SamplerResult

# TODO import _circuit_key from terra once 0.23 released
from .options import Options
from .options.utils import set_default_error_levels
from .runtime_job import RuntimeJob
from .ibm_backend import IBMBackend
from .session import get_default_session
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
        session: Optional[Union[Session, str, IBMBackend]] = None,
        options: Optional[Union[Dict, Options]] = None,
    ):
        """Initializes the Sampler primitive.

        Args:
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
        """
        # `self._options` in this class is a Dict.
        # The base class, however, uses a `_run_options` which is an instance of
        # qiskit.providers.Options. We largely ignore this _run_options because we use
        # a nested dictionary to categorize options.

        super().__init__()

        backend = None
        self._session: Session = None

        if options is None:
            self._options = asdict(Options())
        elif isinstance(options, Options):
            self._options = asdict(copy.deepcopy(options))
        else:
            options_copy = copy.deepcopy(options)
            default_options = asdict(Options())
            self._options = Options._merge_options(default_options, options_copy)

        if isinstance(session, Session):
            self._session = session
        else:
            backend = session or backend
            self._session = get_default_session(None, backend)

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

        backend_obj: Optional[IBMBackend] = None
        if self._session.backend():
            backend_obj = self._session.service.backend(self._session.backend())
            combined = set_default_error_levels(
                combined,
                backend_obj,
                Options._DEFAULT_OPTIMIZATION_LEVEL,
                Options._DEFAULT_RESILIENCE_LEVEL,
            )
        else:
            combined["optimization_level"] = Options._DEFAULT_OPTIMIZATION_LEVEL
            combined["resilience_level"] = Options._DEFAULT_RESILIENCE_LEVEL
        logger.info("Submitting job using options %s", combined)
        Sampler._validate_options(combined)
        inputs.update(Options._get_program_inputs(combined))

        if backend_obj and combined["transpilation"]["skip_transpilation"]:
            for circ in circuits:
                backend_obj.check_faulty(circ)

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
        Sampler._validate_options(combined)
        inputs.update(Options._get_program_inputs(combined))

        raw_result = self._session.run(
            program_id=self._PROGRAM_ID,
            inputs=inputs,
            options=Options._get_runtime_options(combined),
        ).result()

        return raw_result

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

    @staticmethod
    def _validate_options(options: dict) -> None:
        """Validate that program inputs (options) are valid
        Raises:
            ValueError: if resilience_level is out of the allowed range.
        """
        if os.getenv("QISKIT_RUNTIME_SKIP_OPTIONS_VALIDATION"):
            return

        if options.get("resilience_level") and not options.get("resilience_level") in [
            0,
            1,
        ]:
            raise ValueError(
                f"resilience_level can only take the values "
                f"{list(range(Options._MAX_RESILIENCE_LEVEL_SAMPLER + 1))} in Sampler"
            )
        Options.validate_options(options)
