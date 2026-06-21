# This code is part of Qiskit.
#
# (C) Copyright IBM 2025-2026.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Pass to replace `measure` and `reset` instructions in non-terminal locations.

This pass replaces them with their mid-circuit versions.
"""

from __future__ import annotations

import warnings
from typing import TYPE_CHECKING

from qiskit.circuit import Measure, Reset
from qiskit.transpiler import TransformationPass
from qiskit.transpiler.passes.utils.remove_final_measurements import calc_final_ops

if TYPE_CHECKING:
    from qiskit.dagcircuit import DAGCircuit
    from qiskit.transpiler import Target


class ConvertToMidCircuitInstructions(TransformationPass):
    """Transpiler pass replacing mid-circuit terminal measure instructions.

    Transpiler pass that replaces terminal measure instructions in non-terminal locations
    with ``MidCircuitMeasure`` instructions. By default, these will be ``measure_2``, but the
    pass accepts custom ``measure_`` definitions. This pass is expected to run after routing, as
    it will check that ``MidCircuitMeasure`` is supported in the corresponding physical qubit.

    Similarly, the pass will replace terminal reset instructions in non-terminal locations
    with ``MidCircuitReset`` instructions, defaulting to ``reset_2``.

    Note that the pass will only act on non-terminal ``measure`` and ``reset`` instances,
    and won't replace existing mid-circuit measurement instructions
    (e.g., ``"measure_2" -> "measure_3"``) or convert any ``MidCircuitMeasure`` instance
    into a ``Measure``.

    Args:
        target: Backend's target instance that contains one or more ``measure_`` instructions.
        mcm_name: Name of the ``measure`` instruction that terminal measure instructions in
            non-terminal locations will be replaced with. This instruction must be contained in
            the target. Defaults to ``measure_2``.
        mcr_name: Name of the ``reset`` instruction that terminal reset instructions in
            non-terminal locations will be replaced with. This instruction must be contained in
            the target. Defaults to ``reset_2``.

    Raises:
        ValueError: If the specified ``mcm_name`` does not conform to the ``measure_`` pattern
            or is not contained in the provided target.
    """

    def __init__(
        self, target: Target, mcm_name: str = "measure_2", mcr_name: str = "reset_2"
    ) -> None:
        super().__init__()
        self.target = target
        if not mcm_name.startswith("measure"):
            raise ValueError(
                "Invalid name for a measure instruction."
                "The provided name must start with `measure`."
            )
        if not mcr_name.startswith("reset"):
            raise ValueError(
                "Invalid name for a reset instruction.The provided name must start with `reset`."
            )
        if mcm_name not in target.operation_names:
            raise ValueError(
                f"{mcm_name} is not supported by the given target. "
                f"Supported operations are: {target.operation_names}"
            )
        if mcr_name not in target.operation_names:
            raise ValueError(
                f"{mcr_name} is not supported by the given target. "
                f"Supported operations are: {target.operation_names}"
            )
        self.mcm_name = mcm_name
        self.mcr_name = mcr_name

    def run(self, dag: DAGCircuit) -> DAGCircuit:
        """Run the pass on a dag."""
        if self.mcm_name != "measure":
            final_measure_nodes = set(calc_final_ops(dag, {"measure"}))
            for node in dag.op_nodes(Measure):
                if node not in final_measure_nodes:
                    node_indices = [dag.find_bit(qarg).index for qarg in node.qargs]
                    if self.target.instruction_supported(self.mcm_name, node_indices):
                        mid_circ_measure = self.target.operation_from_name(self.mcm_name)
                        dag.substitute_node(node, mid_circ_measure, inplace=True)
                    else:
                        warnings.warn(
                            f"{self.mcm_name} with qubits {node_indices} is not supported "
                            f"by the given target."
                        )

        if self.mcr_name != "reset":
            final_reset_nodes = set(calc_final_ops(dag, {"reset"}))
            for node in dag.op_nodes(Reset):
                if node not in final_reset_nodes:
                    node_indices = [dag.find_bit(qarg).index for qarg in node.qargs]
                    if self.target.instruction_supported(self.mcr_name, node_indices):
                        mid_circ_reset = self.target.operation_from_name(self.mcr_name)
                        dag.substitute_node(node, mid_circ_reset, inplace=True)
                    else:
                        warnings.warn(
                            f"{self.mcr_name} with qubits {node_indices} is not supported "
                            f"by the given target."
                        )

        return dag
