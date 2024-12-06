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
import numpy as np

from qiskit.circuit import QuantumCircuit
from qiskit.circuit.parameter import Parameter
from qiskit.transpiler.passmanager import PassManager
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit.quantum_info import Operator

from qiskit_ibm_runtime.transpiler.passes.basis import FoldRzzAngle
from qiskit_ibm_runtime.fake_provider import FakeFractionalBackend
from .....ibm_test_case import IBMTestCase


@ddt
class TestFoldRzzAngle(IBMTestCase):
    """Test FoldRzzAngle pass"""

    @named_data(
        ("pi/2_pos", pi / 2),
        ("pi/2_neg", -pi / 2),
        ("pi_pos", pi),
        ("pi_neg", -pi),
        ("quad1_no_wrap", 0.1),
        ("quad2_no_wrap", pi / 2 + 0.1),
        ("quad3_no_wrap", -pi + 0.1),
        ("quad4_no_wrap", -0.1),
        ("quad1_2pi_wrap", 2 * pi + 0.1),
        ("quad2_2pi_wrap", -3 * pi / 2 + 0.1),
        ("quad3_2pi_wrap", pi + 0.1),
        ("quad4_2pi_wrap", 2 * pi - 0.1),
        ("quad1_12pi_wrap", -12 * pi + 0.1),
        ("quad2_12pi_wrap", 23 * pi / 2 + 0.1),
        ("quad3_12pi_wrap", 11 * pi + 0.1),
        ("quad4_12pi_wrap", -12 * pi - 0.1),
    )
    def test_folding_rzz_angles(self, angle):
        """Test folding gate angle into calibrated range."""
        qc = QuantumCircuit(2)
        qc.rzz(angle, 0, 1)
        pm = PassManager([FoldRzzAngle()])
        isa = pm.run(qc)

        self.assertEqual(Operator.from_circuit(qc), Operator.from_circuit(isa))
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

    def test_controlflow(self):
        """Test non-ISA Rzz gates inside/outside a control flow branch."""
        qc = QuantumCircuit(2, 1)
        qc.rzz(-0.2, 0, 1)
        with qc.if_test((0, 1)):  # pylint: disable=not-context-manager
            qc.rzz(-0.1, 0, 1)
            with qc.if_test((0, 1)):  # pylint: disable=not-context-manager
                qc.rzz(-0.3, 0, 1)

        pm = PassManager([FoldRzzAngle()])
        isa = pm.run(qc)

        expected = QuantumCircuit(2, 1)
        expected.x(0)
        expected.rzz(0.2, 0, 1)
        expected.x(0)
        with expected.if_test((0, 1)):  # pylint: disable=not-context-manager
            expected.x(0)
            expected.rzz(0.1, 0, 1)
            expected.x(0)
            with expected.if_test((0, 1)):  # pylint: disable=not-context-manager
                expected.x(0)
                expected.rzz(0.3, 0, 1)
                expected.x(0)

        self.assertEqual(isa, expected)

    def test_fractional_plugin(self):
        """Verify that a pass manager created for a fractional backend applies the rzz folding
        pass"""

        circ = QuantumCircuit(2)
        circ.rzz(7, 0, 1)

        pm = generate_preset_pass_manager(
            optimization_level=0,
            backend=FakeFractionalBackend(),
            translation_method="ibm_fractional",
        )
        isa_circ = pm.run(circ)

        self.assertEqual(isa_circ.data[0].operation.name, "global_phase")
        self.assertEqual(isa_circ.data[1].operation.name, "rzz")
        self.assertTrue(np.isclose(isa_circ.data[1].operation.params[0], 7 - 2 * pi))
