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

"""SimRuntimeJob: local simulation jobs via ``qiskit-aer``."""

from __future__ import annotations

from typing import TYPE_CHECKING

from qiskit.primitives.primitive_job import PrimitiveJob

from .run_quantum_program import run_quantum_program

if TYPE_CHECKING:
    from qiskit.primitives.containers.primitive_result import PrimitiveResult
    from qiskit.providers import BackendV2

    from ..options_models.simulator import ExperimentalSimulatorOptions
    from ..quantum_program import QuantumProgram
    from ..results import QuantumProgramResult


class SimRuntimeJob(PrimitiveJob):
    """Job object for running local-mode simulations via qiskit-aer.

    **Noise injection**

    When ``noise_model`` is provided in :class:`~.ExperimentalSimulatorOptions`, Pauli-Lindblad
    noise is injected into circuits at tagged barriers via :class:`~.InsertNoisePass`.  Samplomatic
    inserts three barriers around each boxed gate — left (``L``), middle (``M``), and right (``R``)
    — with labels of the form ``<pos><idx>@tag=<tag>`` (e.g. ``R0@tag=r0``).  By default,
    noise is injected at the ``R`` (right) barriers, i.e. *after* the gate.  Use
    ``noise_after=False`` on :class:`~.InsertNoisePass` to target ``M`` barriers instead
    (noise *before* the gate).

    The ``noise_model`` format is:

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
        program: The quantum program to execute.
        options: The simulator options to use.
    """

    def __init__(
        self,
        backend: BackendV2,
        program: QuantumProgram,
        options: ExperimentalSimulatorOptions,
    ):
        super().__init__(
            function=run_quantum_program,
            backend=backend,
            program=program,
            options=options,
        )

        self._submit()

    def result(self) -> QuantumProgramResult | PrimitiveResult:
        """Return the post-processed results of the job.

        Returns:
            IBM Quantum Compute job result (post-processed if applicable).
        """
        from ..decoders.quantum_program.decoder import QuantumProgramResultDecoder

        return QuantumProgramResultDecoder._apply_post_processing(super().result())
