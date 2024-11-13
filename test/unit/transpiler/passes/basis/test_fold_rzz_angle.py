# This code is part of Qiskit.
#
# (C) Copyright IBM 2024.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Test folding Rzz angle into calibrated range."""

from math import pi
from ddt import ddt, named_data

from qiskit.circuit import QuantumCircuit
from qiskit.quantum_info import Operator
from qiskit.transpiler.passmanager import PassManager
from qiskit.circuit.parameter import Parameter

from qiskit_ibm_runtime.transpiler.passes.basis import FoldRzzAngle
from .....ibm_test_case import IBMTestCase


@ddt
class TestFoldRzzAngle(IBMTestCase):
    """Test FoldRzzAngle pass"""

    @named_data(
        ("large_positive_number", 12345),
        ("large_negative_number", -12345),
        ("pi/2_pos", pi / 2),
        ("pi/2_neg", -pi / 2),
        ("pi_pos", pi),
        ("pi_neg", -pi),
        ("quad1", 0.1),
        ("quad2", pi / 2 + 0.1),
        ("quad3", -pi + 0.1),
        ("quad4", -0.1),
    )
    def test_folding_rzz_angles(self, angle):
        """Test folding gate angle into calibrated range."""
        qc = QuantumCircuit(2)
        qc.rzz(angle, 0, 1)
        pm = PassManager([FoldRzzAngle()])
        isa = pm.run(qc)

        self.assertTrue(Operator.from_circuit(qc).equiv(Operator.from_circuit(isa)))
        for inst_data in isa.data:
            if inst_data.operation.name == "rzz":
                fold_angle = inst_data.operation.params[0]
                self.assertGreaterEqual(fold_angle, 0.0)
                self.assertLessEqual(fold_angle, pi / 2)

    def test_folding_rzz_angle_unbound(self):
        """Test skip folding unbound gate angle."""
        qc = QuantumCircuit(2)
        qc.rzz(Parameter("θ"), 0, 1)
        pm = PassManager([FoldRzzAngle()])
        isa = pm.run(qc)
        self.assertEqual(qc, isa)
