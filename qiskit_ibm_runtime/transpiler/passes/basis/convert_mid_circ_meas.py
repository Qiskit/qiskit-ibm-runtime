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

"""Pass to convert measurements in the middle of the circuit to MidCircuitMeasure instances."""

from qiskit.transpiler.basepasses import TransformationPass
from qiskit.circuit.measure import Measure
from qiskit.transpiler.passes.utils.remove_final_measurements import calc_final_ops

class ConvertToMidCircuitMeasure(TransformationPass):
    """This pass replaces terminal measures in the middle of the circuit with 
    MidCircuitMeasure instructions.
    """

    def __init__(self, target):
        super().__init__()
        self.target = target

    def run(self, dag):
        """Run the pass on a dag."""
        mid_circ_measure = None
        for inst in self.target.instructions:
            if inst[0].name.startswith("measure_"):
                mid_circ_measure = inst[0]
                break
        if not mid_circ_measure:
            return dag

        final_measure_nodes = calc_final_ops(dag, {"measure"})

        for node in dag.op_nodes(Measure):
            if node not in final_measure_nodes:
                dag.substitute_node(node, mid_circ_measure, inplace=True)

        return dag