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

"""Test the conversion of Id gate operations to a delay."""

from qiskit.circuit import QuantumCircuit
from qiskit.transpiler.passmanager import PassManager

from qiskit_ibm_runtime.transpiler.passes.basis.convert_id_to_delay import (
    ConvertIdToDelay,
)

from qiskit_ibm_runtime.transpiler.passes.scheduling.utils import (
    DynamicCircuitInstructionDurations,
)

from .....ibm_test_case import IBMTestCase

# pylint: disable=invalid-name


class TestConvertIdToDelay(IBMTestCase):
    """Tests the ConvertIdToDelay pass"""

    def setUp(self):
        """Setup."""
        super().setUp()

        self.durations = DynamicCircuitInstructionDurations([("sx", None, 160), ("x", None, 200)])

    def test_id_gate(self):
        """Test if Id gate is converted a delay."""
        qc = QuantumCircuit(1, 0)
        qc.id(0)

        pm = PassManager([ConvertIdToDelay(self.durations)])
        transformed = pm.run(qc)

        expected = QuantumCircuit(1, 0)
        expected.delay(160, 0)

        self.assertEqual(expected, transformed)

    def test_id_gate_unit(self):
        """Test if Id gate is converted a delay with correct units."""
        qc = QuantumCircuit(1, 0)
        qc.id(0)

        pm = PassManager([ConvertIdToDelay(self.durations, "x")])
        transformed = pm.run(qc)

        expected = QuantumCircuit(1, 0)
        expected.delay(200, 0)

        self.assertEqual(expected, transformed)

    def test_c_if_id_gate(self):
        """Test if c_if Id gate is converted a c_if delay."""
        qc = QuantumCircuit(1, 1)

        with qc.if_test((0, 1)):  # pylint: disable=not-context-manager
            qc.id(0)

        pm = PassManager([ConvertIdToDelay(self.durations)])
        transformed = pm.run(qc)

        expected = QuantumCircuit(1, 1)
        with expected.if_test((0, 1)):  # pylint: disable=not-context-manager
            expected.delay(160, 0)

        self.assertEqual(expected, transformed)

    def test_if_test_id_gate(self):
        """Test if if_test Id gate is converted a if_test delay."""
        qc = QuantumCircuit(1, 1)
        with qc.if_test((0, 1)) as else_:  # pylint: disable=not-context-manager
            qc.id(0)
        with else_:  # pylint: disable=not-context-manager
            qc.id(0)

        pm = PassManager([ConvertIdToDelay(self.durations)])
        transformed = pm.run(qc)

        expected = QuantumCircuit(1, 1)
        with expected.if_test((0, 1)) as else_:  # pylint: disable=not-context-manager
            expected.delay(160, 0)
        with else_:
            expected.delay(160, 0)

        self.assertEqual(expected, transformed)
