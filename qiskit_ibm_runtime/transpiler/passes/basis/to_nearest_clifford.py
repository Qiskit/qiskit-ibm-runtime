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
Pass to convert the :class:`qiskit.circuit.gate.Gate`\s of an ISA circuit to the nearest Clifford
gate.
"""

import numpy as np

from qiskit.circuit.library import CXGate, CZGate, ECRGate, RZGate, SXGate, XGate
from qiskit.dagcircuit import DAGCircuit
from qiskit.transpiler.basepasses import TransformationPass

SUPPORTED_GATES = (CXGate, CZGate, ECRGate, XGate, SXGate, RZGate)
"""The set of gates supported by the :class:`~.ToNearestClifford` pass."""


class ToNearestClifford(TransformationPass):
    """
    Convert the :class:`qiskit.circuit.gate.Gate`\s of an ISA circuit to the nearest Clifford gate.

    This pass can be used to uniquely map an ISA circuit to a Clifford circuit. To do so,
    it replaces every :class:`qiskit.circuit.library.RZGate` by angle :math:`\phi`
    with a corresponding rotation by angle :math:`\phi'`, where :math:`\phi'` is the
    multiple of :math:`\pi/2` closest to :math:`\phi`\. It skips
    :class:`qiskit.circuit.library.CXGate`\s, :class:`qiskit.circuit.library.CZGate`\s,
    :class:`qiskit.circuit.library.ECRGate`\s, :class:`qiskit.circuit.library.SXGate`\s,
    and :class:`qiskit.circuit.library.XGate`\s, and it errors for every other gate.
    """

    def __init__(self):
        """Convert :class:`qiskit.circuit.gate.Gate`\s to the nearest Clifford gate."""
        super().__init__()

    def run(self, dag: DAGCircuit) -> DAGCircuit:
        for node in dag.op_nodes():
            if not isinstance(node.op, SUPPORTED_GATES):
                msg = f"Gate ``{node.op.__class__.__name__}`` is not supported."
                raise ValueError(msg)
            if isinstance(node.op, RZGate):
                angle = node.op.params[0]
                rem = angle % (np.pi / 2)
                new_angle = angle - rem if rem < np.pi / 4 else angle + np.pi / 2 - rem
                dag.substitute_node(node, RZGate(new_angle), inplace=True)
        return dag
