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

"""Pass to replace mid-circuit instructions with their standard counterparts for simulation."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from qiskit.circuit import ControlFlowOp, Measure, Reset
from qiskit.circuit.controlflow import CONTROL_FLOW_OP_NAMES
from qiskit.converters import circuit_to_dag, dag_to_circuit
from qiskit.transpiler import TransformationPass
from qiskit.transpiler.passes.utils.control_flow import trivial_recurse

if TYPE_CHECKING:
    from qiskit.circuit import Instruction, Operation, QuantumCircuit
    from qiskit.dagcircuit import DAGCircuit

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


class ConvertMidCircuitToStandard(TransformationPass):
    """Transpiler pass replacing mid-circuit measure and reset instructions for simulation.

    Simulators such as Aer do not support the mid-circuit instructions advertised by some
    backends. This pass replaces every single-qubit ``measure_<n>`` instruction (e.g.
    ``measure_2``) with a :class:`~qiskit.circuit.Measure`, and every single-qubit ``reset_<n>``
    instruction (e.g. ``reset_2``) with a :class:`~qiskit.circuit.Reset`, where ``<n>`` is an
    integer, including inside control-flow blocks. Instructions are matched by name, as backend
    targets define them as generic instructions.

    Other instructions, such as ``measure_reset``, are left unchanged.
    """

    @trivial_recurse
    def run(self, dag: DAGCircuit) -> DAGCircuit:
        """Run the pass on a dag."""
        for node in dag.op_nodes():
            if (replacement := _standard_replacement(node.op)) is not None:
                dag.substitute_node(node, replacement, inplace=True)
        return dag


def _has_mid_circuit_instructions(circuit: QuantumCircuit) -> bool:
    """Return whether ``circuit`` contains instructions replaced by the conversion pass."""
    op_names = circuit.count_ops().keys()
    if CONTROL_FLOW_OP_NAMES.isdisjoint(op_names) and not any(
        _MID_CIRCUIT_NAME.fullmatch(name) for name in op_names
    ):
        return False
    for instruction in circuit.data:
        operation = instruction.operation
        if _standard_replacement(operation) is not None:
            return True
        if isinstance(operation, ControlFlowOp) and any(
            _has_mid_circuit_instructions(block) for block in operation.blocks
        ):
            return True
    return False


def convert_mid_circuit_instructions(circuit: QuantumCircuit) -> QuantumCircuit:
    """Replace the mid-circuit instructions in ``circuit`` so it can be simulated.

    Args:
        circuit: The circuit to convert. It is not modified.

    Returns:
        A converted copy of ``circuit``, or ``circuit`` itself if it contains no mid-circuit
        instructions.
    """
    if not _has_mid_circuit_instructions(circuit):
        return circuit
    converted_dag = ConvertMidCircuitToStandard().run(circuit_to_dag(circuit))
    converted = dag_to_circuit(converted_dag, copy_operations=False)
    # The layout is not part of the DAG. Qiskit's PassManager also restores it via ``_layout``,
    # as ``QuantumCircuit.layout`` has no setter.
    converted._layout = circuit._layout
    return converted
