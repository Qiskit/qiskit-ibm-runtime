# This code is part of Qiskit.
#
# (C) Copyright IBM 2026.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""SimExecutor and SimRuntimeJob: local simulation executor for QuantumProgram."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from qiskit.utils.optionals import HAS_AER

from .run_quantum_program import run_quantum_program

if TYPE_CHECKING:
    from qiskit.providers import BackendV2

    from ..options_models.simulator import SimulatorOptions
    from ..quantum_program import QuantumProgram
    from ..results import QuantumProgramResult


@HAS_AER.require_in_instance
class SimRuntimeJob:
    """Job object returned by :meth:`~.SimExecutor.run`.

    The program is executed eagerly on construction; the result is available
    immediately when :meth:`result` is called.

    Args:
        backend: The backend to simulate.
        program: The quantum program to execute.
        options: The simulator options to use.
    """

    def __init__(
        self,
        backend: BackendV2,
        program: QuantumProgram,
        options: SimulatorOptions,
    ):
        self._backend = backend
        self._program = program
        self._options = options

        self._job_id: str = str(uuid.uuid4())
        self.tags: list[str] = []  # interface compatibility with real Executor

        self._result = None

    def job_id(self) -> str:
        """Return the unique job ID."""
        return self._job_id

    def result(self, *_, **__) -> QuantumProgramResult:  # type: ignore[no-untyped-def]
        """Return the result of the program execution."""
        if self._result is None:
            options = self._options
            self._result = run_quantum_program(
                backend=self._backend,
                program=self._program,
                noise_dict=options.noise_model,
                angle_decimals=options.angle_decimals,
                warn_absent=options.warn_absent,
            )
        return self._result


@HAS_AER.require_in_instance
class SimExecutor:
    """Local Aer-based executor mimicking the IBM Runtime executor interface.

    Runs a :class:`~qiskit_ibm_runtime.QuantumProgram` eagerly on construction of the
    returned job — the result is available immediately when :meth:`~.SimRuntimeJob.result`
    is called.

    **Noise injection**

    When ``noise_dict`` is provided, Pauli-Lindblad noise is injected into circuits at
    tagged barriers via :class:`~.InsertNoisePass`.  Samplomatic inserts three barriers
    around each boxed gate — left (``L``), middle (``M``), and right (``R``) — with
    labels of the form ``<pos><idx>@tag=<tag>`` (e.g. ``R0@tag=r0``).  By default,
    noise is injected at the ``R`` (right) barriers, i.e. *after* the gate.  Use
    ``noise_after=False`` on :class:`~.InsertNoisePass` to target ``M`` barriers instead
    (noise *before* the gate).

    The ``noise_dict`` format is:

    - **Keys** — layer name tags (strings, e.g. ``"r0"``, ``"my_tag"``).  Each key must match
      the ``ref`` of a ``Tag`` annotation used when building the ``QuantumProgram``.
      A warning is emitted (if ``warn_absent=True``) when a tagged barrier's tag is absent
      from the dict; the barrier is left as-is (no noise inserted for that layer).
    - **Values** — :class:`~qiskit.quantum_info.PauliLindbladMap` instances describing
      the Pauli-Lindblad noise channel for that gate.  The map's ``num_qubits`` must
      equal the number of qubits on the corresponding barrier in the circuit.
    - **Qubit indexing** — indices inside the map are *local* to the barrier's qubit
      set, independent of global circuit qubit numbering.

    Args:
        backend: The backend to simulate.
        options: The simulator options.
    """

    def __init__(
        self,
        backend: BackendV2,
        options: SimulatorOptions,
    ):
        self._backend = backend
        self._options = options

    def run(self, program: QuantumProgram) -> SimRuntimeJob:
        """Run a quantum program and return a completed job.

        Args:
            program: The quantum program to execute.

        Returns:
            A job whose result is immediately available.
        """
        return SimRuntimeJob(
            backend=self._backend,
            program=program,
            options=self._options,
        )
