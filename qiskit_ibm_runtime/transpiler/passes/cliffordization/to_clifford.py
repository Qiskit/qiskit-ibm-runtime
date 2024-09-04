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

"""
Pass to convert the gates of a circuit to Clifford gates.
"""

from random import choices
import numpy as np

from qiskit.circuit import Barrier, Measure
from qiskit.circuit.library import CXGate, CZGate, ECRGate, IGate, RZGate, SXGate, XGate
from qiskit.dagcircuit import DAGCircuit
from qiskit.transpiler.basepasses import TransformationPass

ISA_SUPPORTED_GATES = (CXGate, CZGate, ECRGate, IGate, RZGate, SXGate, XGate)
"""
The set of gates that can be found in an ISA circuit.
"""

SUPPORTED_INSTRUCTIONS = (Barrier, Measure)
"""An additional set of instructions allowed by the :class:`~.ToClifford` pass."""


class ToClifford(TransformationPass):
    """
    Convert the gates of an ISA circuit to Clifford gates.

    ISA circuits contain only Clifford gates from a restricted set or
    :class:`qiskit.circuit.library.RZGate`\\s by arbitrary angles. To map them to Clifford
    circuits, this pass rounds the angle of every :class:`qiskit.circuit.library.RZGate` to the
    closest multiple of `pi/2` (or to a random multiple of `pi/2` if the angle is unspecified),
    while it skips every Clifford gate, measurement, and barrier, and it errors for every non-ISA
    non-Clifford gate.

    .. code-block:: python

        import numpy as np

        from qiskit.circuit import QuantumCircuit, Parameter
        from qiskit.transpiler import PassManager
        from qiskit_ibm_runtime.transpiler.passes import ToClifford

        # An ISA circuit ending with a Z rotation by pi/3
        qc = QuantumCircuit(2, 2)
        qc.sx(0)
        qc.rz(np.pi/2, 0)
        qc.sx(0)
        qc.barrier()
        qc.cx(0, 1)
        qc.rz(np.pi/3, 0)  # non-Clifford Z rotation
        qc.rz(Parameter("th"), 0)  # Z rotation with unspecified angle

        # Turn into a Clifford circuit
        pm = PassManager([ToClifford()])
        clifford_qc = pm.run(qc)

    Raises:
        ValueError: If the given circuit contains unsupported operations, such as non-Clifford
            gates that are not Pauli-Z rotations.
    """

    def run(self, dag: DAGCircuit) -> DAGCircuit:
        for node in dag.op_nodes():
            if not isinstance(node.op, ISA_SUPPORTED_GATES + SUPPORTED_INSTRUCTIONS):
                raise ValueError(f"Operation ``{node.op.name}`` not supported.")

            # Rounds the angle of `RZ`s to a multiple of pi/2 and skip every other supported
            # instruction.
            if isinstance(node.op, RZGate):
                if isinstance(angle := node.op.params[0], float):
                    rem = angle % (np.pi / 2)
                    new_angle = angle - rem if rem < np.pi / 4 else angle + np.pi / 2 - rem
                else:
                    # special handling of parametric gates
                    new_angle = choices([0, np.pi / 2, np.pi, 3 * np.pi / 2])[0]
                dag.substitute_node(node, RZGate(new_angle), inplace=True)

        return dag
