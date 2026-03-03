# This code is part of Qiskit.
#
# (C) Copyright IBM 2025.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Pass to replace terminal measures in the middle of the circuit with
MidCircuitMeasure instructions."""

from qiskit.circuit import Measure
from qiskit.dagcircuit import DAGCircuit
from qiskit.transpiler import TransformationPass, Target
from qiskit.transpiler.passes.utils.remove_final_measurements import calc_final_ops


class ConvertToMidCircuitMeasure(TransformationPass):
    """This pass replaces terminal measures in the middle of the circuit with
    MidCircuitMeasure instructions.
    """

    def __init__(self, target: Target, mcm_name: str = "measure_2") -> None:
        """Transpiler pass that replaces terminal measure instructions in non-terminal locations with
        ``MidCircuitMeasure`` instructions. By default, these will be ``measure_2``, but the pass accepts
        custom ``measure_`` definitions. This pass is expected to run after routing, as it will check
        that ``MidCircuitMeasure`` is supported in the corresponding physical qubit.

        Note that the pass will only act on non-terminal ``Measure`` instances, and won't replace
        existing mid-circuit measurement instructions (e.g., ``"measure_2" -> "measure_3"``) or
        convert any ``MidCircuitMeasure`` instance into a ``Measure``.

        Args:
            target: Backend's target instance that contains one or more ``measure_`` instructions.
            mcm_name: Name of the ``measure_`` instruction that terminal measure instructions in
                non-terminal locations will be replaced with. This instruction must be contained in
                the target. Defaults to ``measure_2``.

        Raises:
            ValueError: If the specifcied ``mcm_name`` does not conform to the ``measure_`` pattern or
                is not contained in the provided target.
        """

        super().__init__()
        self.target = target
        if not mcm_name.startswith("measure_"):
            raise ValueError(
                "Invalid name for mid-circuit measure instruction."
                "The provided name must start with `measure_`."
            )
        if mcm_name not in target.operation_names:
            raise ValueError(
                f"{mcm_name} is not supported by the given target. "
                f"Supported operations are: {target.operation_names}"
            )
        self.mcm_name = mcm_name

    def run(self, dag: DAGCircuit) -> DAGCircuit:
        """Run the pass on a dag."""
        final_measure_nodes = calc_final_ops(dag, {"measure"})
        for node in dag.op_nodes(Measure):
            if node not in final_measure_nodes:
                node_indices = [dag.find_bit(qarg).index for qarg in node.qargs]
                # only replace Measure with MidCircuitMeasure if MidCircuitMeasure
                # is supported in the corresponding qargs
                if self.target.instruction_supported(self.mcm_name, node_indices):
                    mid_circ_measure = self.target.operation_from_name(self.mcm_name)
                    dag.substitute_node(node, mid_circ_measure, inplace=True)

        return dag
