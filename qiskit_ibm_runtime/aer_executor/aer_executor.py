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

"""AerExecutor and AerRuntimeJob: local simulation executor for QuantumProgram objects."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from qiskit.utils.optionals import HAS_AER

from .run_quantum_program import run_quantum_program

if TYPE_CHECKING:
    from qiskit.providers import BackendV2
    from qiskit.quantum_info import PauliLindbladMap

    from ..quantum_program import QuantumProgram
    from ..results import QuantumProgramResult


class AerRuntimeJob:
    """Job object returned by :meth:`AerExecutor.run`.

    The program is executed eagerly on construction; the result is available
    immediately when :meth:`result` is called.

    Args:
        qasm_simulator: The Aer simulator to run on.
        program: The quantum program to execute.
        noise_dict: A map from barrier label refs to Pauli-Lindblad noise maps.
        angle_decimals: Rounding precision for gate angles (in units of π/2).
        warn_absent: If ``True`` (default), warn when a tagged barrier has no entry in
            ``noise_dict``.
    """

    def __init__(
        self,
        qasm_simulator: BackendV2,
        program: QuantumProgram,
        noise_dict: dict[str, PauliLindbladMap] | None = None,
        angle_decimals: int = 5,
        warn_absent: bool = True,
    ):
        if not HAS_AER:
            raise ValueError(
                "Cannot initialize object of type 'AerExecutor' since 'qiskit-aer' is not "
                "installed. Install 'qiskit-aer' and try again."
            )

        from qiskit_aer import AerSimulator

        if not isinstance(qasm_simulator, AerSimulator):
            raise ValueError("``qasm_simulator`` needs to be an ``AerSimulator`` object.")

        self._qasm_simulator = qasm_simulator
        self._program = program
        self._noise_dict = noise_dict
        self._angle_decimals = angle_decimals
        self._warn_absent = warn_absent
        self._job_id: str = str(uuid.uuid4())
        self.tags: list[str] = []  # interface compatibility with real Executor

        self._result = run_quantum_program(
            qasm_simulator=self._qasm_simulator,
            program=self._program,
            noise_dict=self._noise_dict,
            angle_decimals=self._angle_decimals,
            warn_absent=self._warn_absent,
        )

    def job_id(self) -> str:
        """Return the unique job ID."""
        return self._job_id

    def result(self, *_, **__) -> QuantumProgramResult:  # type: ignore[no-untyped-def]
        """Return the result of the program execution."""
        return self._result


class AerExecutor:
    """Local Aer-based executor mimicking the IBM Runtime executor interface.

    Runs a :class:`~qiskit_ibm_runtime.QuantumProgram` eagerly on construction of the
    returned job — the result is available immediately when :meth:`AerRuntimeJob.result`
    is called.

    **Noise injection**

    When ``noise_dict`` is provided, Pauli-Lindblad noise is injected into circuits at
    tagged barriers via :class:`~.InsertNoisePass`.  Samplomatic inserts three barriers
    around each boxed gate — left (``L``), middle (``M``), and right (``R``) — with
    labels of the form ``<pos><idx>@tag=<tag>`` (e.g. ``R0@tag=r0``).  By default,
    noise is injected at the ``R`` (right) barriers, i.e. *after* the gate.  Use
    ``noise_after=False`` on :class:`InsertNoisePass` to target ``M`` barriers instead
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
        qasm_simulator: The Aer simulator to run programs on.
        noise_dict: A map from barrier label refs to Pauli-Lindblad noise maps.  Pass
            ``None`` (default) to run without noise injection.
        angle_decimals: Gate angles are rounded to the nearest multiple of π/2 at this
            decimal precision before simulation.  This prevents floating-point drift from
            preventing Clifford-method simulation when angles are nominally Clifford.
        warn_absent: If ``True`` (default), emit a warning when a tagged barrier's tag is
            not found in ``noise_dict``.  Set to ``False`` when partial coverage of tags is
            intentional.
    """

    def __init__(
        self,
        qasm_simulator: BackendV2,
        noise_dict: dict[str, PauliLindbladMap] | None = None,
        angle_decimals: int = 5,
        warn_absent: bool = True,
    ):
        if not HAS_AER:
            raise ValueError(
                "Cannot initialize object of type 'AerExecutor' since 'qiskit-aer' is not "
                "installed. Install 'qiskit-aer' and try again."
            )

        from qiskit_aer import AerSimulator

        if not isinstance(qasm_simulator, AerSimulator):
            raise ValueError("``qasm_simulator`` needs to be an ``AerSimulator`` object.")

        self._qasm_simulator = qasm_simulator
        self._noise_dict = noise_dict
        self._angle_decimals = angle_decimals
        self._warn_absent = warn_absent

    def run(self, program: QuantumProgram) -> AerRuntimeJob:
        """Run a quantum program and return a completed job.

        Args:
            program: The quantum program to execute.

        Returns:
            A job whose result is immediately available.
        """
        return AerRuntimeJob(
            qasm_simulator=self._qasm_simulator,
            program=program,
            noise_dict=self._noise_dict,
            angle_decimals=self._angle_decimals,
            warn_absent=self._warn_absent,
        )
