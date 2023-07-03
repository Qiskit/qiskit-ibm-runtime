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
import logging

from qiskit.circuit import QuantumCircuit
from qiskit.primitives import BaseSampler

from .options import Options
from .runtime_job import RuntimeJob
from .ibm_backend import IBMBackend
from .base_primitive import BasePrimitive

# pylint: disable=unused-import,cyclic-import
from .session import Session

logger = logging.getLogger(__name__)


class Sampler(BasePrimitive, BaseSampler):
    """Class for interacting with Qiskit Runtime Sampler primitive service.

    Qiskit Runtime Sampler primitive service calculates quasi-probability distribution
    of bitstrings from quantum circuits.

    The :meth:`run` method can be used to submit circuits and parameters to the Sampler primitive.

    You are encouraged to use :class:`~qiskit_ibm_runtime.Session` to open a session,
    during which you can invoke one or more primitives. Jobs submitted within a session
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

            # You can run more jobs inside the session

            # Close the session only if all jobs are finished
            # and you don't need to run more in the session.
            session.close()
    """

    def __init__(
        self,
        backend: Optional[Union[str, IBMBackend]] = None,
        session: Optional[Union[Session, str, IBMBackend]] = None,
        options: Optional[Union[Dict, Options]] = None,
    ):
        """Initializes the Sampler primitive.

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
        BaseSampler.__init__(self)
        BasePrimitive.__init__(self, backend=backend, session=session, options=options)

    def run(  # pylint: disable=arguments-differ
        self,
        circuits: QuantumCircuit | Sequence[QuantumCircuit],
        parameter_values: Sequence[float] | Sequence[Sequence[float]] | None = None,
        **kwargs: Any,
    ) -> RuntimeJob:
        """Submit a request to the sampler primitive.

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
        """Submit a request to the sampler primitive.

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
        return self._run_primitive(
            primitive_inputs=inputs, user_kwargs=kwargs.get("_user_kwargs", {})
        )

    def _validate_options(self, options: dict) -> None:
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

    @classmethod
    def _program_id(cls) -> str:
        """Return the program ID."""
        return "sampler"
