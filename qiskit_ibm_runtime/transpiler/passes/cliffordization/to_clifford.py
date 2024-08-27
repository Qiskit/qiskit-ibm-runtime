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
Pass to convert the :class:`qiskit.circuit.gate.Gate`\\s of a circuit to a Clifford gate.
"""

import numpy as np
from random import choices

from qiskit.circuit import Barrier, Instruction, Measure
from qiskit.circuit.library import CXGate, CZGate, ECRGate, IGate, RZGate, SXGate, XGate
from qiskit.exceptions import QiskitError
from qiskit.quantum_info import Clifford
from qiskit.dagcircuit import DAGCircuit
from qiskit.transpiler.basepasses import TransformationPass

ISA_SUPPORTED_GATES = (CXGate, CZGate, ECRGate, IGate, RZGate, SXGate, XGate)
"""
The set of gates that can be found in an ISA circuit, handled fastly by the :class:`~.ToClifford`
pass.
"""

SUPPORTED_INSTRUCTIONS = (Barrier, Measure)
"""An additional set of instructions handled fastly by the :class:`~.ToClifford` pass."""


def _is_clifford(instruction: Instruction) -> bool:
    r"""
    Checks if an instruction is a valid Clifford gate by trying to cast it as a Clifford object.
    """
    try:
        Clifford(instruction)
    except QiskitError:
        return False
    return True


class ToClifford(TransformationPass):
    """
    Convert the gates of a circuit to Clifford gates.

    This pass is optimized to run efficiently on ISA circuits, which contain only Clifford gates
    from a restricted set or :class:`qiskit.circuit.library.RZGate`\\s by arbitrary angles. To do
    so, it rounds the angle of every :class:`qiskit.circuit.library.RZGate` to the closest multiple
    of `pi/2` (or to a random multiple of `pi/2` if the angle is unspecified). It skips every
    Clifford gate, measurement, and barrier, and it errors for every non-ISA non-Clifford gate.

    .. code-block:: python

        import numpy as np

        from qiskit.circuit import QuantumCircuit, Parameter
        from qiskit.transpiler import PassManager
        from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

        from qiskit_ibm_runtime.fake_provider import FakeKyiv
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
            if isinstance(node.op, ISA_SUPPORTED_GATES + SUPPORTED_INSTRUCTIONS):
                # Fast handling of ISA gates. It rounds the angle of `RZ`s to a multiple of pi/2,
                # while skipping every other supported gates and instructions.
                if isinstance(node.op, RZGate):
                    if isinstance(angle := node.op.params[0], float):
                        rem = angle % (np.pi / 2)
                        new_angle = angle - rem if rem < np.pi / 4 else angle + np.pi / 2 - rem
                    else:
                        # special handling of parametric gates
                        new_angle = choices([0, np.pi / 2, np.pi, 3 * np.pi / 2])[0]
                    dag.substitute_node(node, RZGate(new_angle), inplace=True)
            else:
                # Handle non-ISA gates, which may be either Clifford or non-Clifford.
                if _is_clifford(node.op):
                    dag.substitute_node(node, node.op, inplace=True)
                else:
                    raise ValueError(f"Operation ``{node.op.name}`` not supported.")
        return dag
