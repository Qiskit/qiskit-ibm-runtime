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

"""Replace mid-circuit instructions with their standard counterparts for simulation."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from qiskit.circuit import ControlFlowOp, Measure, Reset

if TYPE_CHECKING:
    from qiskit.circuit import Instruction, Operation, QuantumCircuit

_MID_CIRCUIT_NAME = re.compile(r"(measure|reset)_\d+")


def _standard_replacement(operation: Operation) -> Instruction | None:
    """Return the standard instruction replacing the mid-circuit ``operation``, if any."""
    if operation.num_qubits != 1 or not _MID_CIRCUIT_NAME.fullmatch(operation.name):
        return None
    if operation.name.startswith("measure_") and operation.num_clbits == 1:
        return Measure()
    if operation.name.startswith("reset_") and operation.num_clbits == 0:
        return Reset()
    return None


def convert_mid_circuit_instructions(circuit: QuantumCircuit) -> QuantumCircuit:
    """Replace the mid-circuit instructions in ``circuit`` so it can be simulated.

    Simulators such as Aer do not support the mid-circuit instructions advertised by some
    backends. This function replaces every single-qubit ``measure_<n>`` instruction (e.g.
    ``measure_2``) with a :class:`~qiskit.circuit.Measure`, and every single-qubit ``reset_<n>``
    instruction (e.g. ``reset_2``) with a :class:`~qiskit.circuit.Reset`, where ``<n>`` is an
    integer, including inside control-flow blocks. Instructions are matched by name, as backend
    targets define them as generic instructions.

    Other instructions, such as ``measure_reset``, are left unchanged.

    Args:
        circuit: The circuit to convert. It is not modified.

    Returns:
        A converted copy of ``circuit``.
    """
    # Starting from an empty copy keeps everything else in the circuit as it is.
    converted = circuit.copy_empty_like()
    for instruction in circuit.data:
        operation = instruction.operation
        if (replacement := _standard_replacement(operation)) is not None:
            instruction = instruction.replace(operation=replacement)
        elif isinstance(operation, ControlFlowOp):
            blocks = [convert_mid_circuit_instructions(block) for block in operation.blocks]
            instruction = instruction.replace(operation=operation.replace_blocks(blocks))
        converted.append(instruction)
    return converted
