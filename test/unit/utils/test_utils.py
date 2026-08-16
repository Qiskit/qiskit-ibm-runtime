# This code is part of Qiskit.
#
# (C) Copyright IBM 2021-2026.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Tests for the functions in the utils file."""

from qiskit.circuit import BoxOp, QuantumCircuit
from qiskit.qpy import QPY_VERSION
from samplomatic.ssv import SSV

from qiskit_ibm_runtime.exceptions import IBMInputValueError
from qiskit_ibm_runtime.utils.utils import get_qpy_version, get_ssv_version, validate_no_boxes

from ...ibm_test_case import IBMTestCase


class TestGetQPYVersion(IBMTestCase):
    """Test for getter of QPY version."""

    def test_no_highest_value(self):
        """Test with unset highest value."""
        self.assertEqual(get_qpy_version(), QPY_VERSION)

    def test_highest_value(self):
        """Test with set highest value."""
        self.assertEqual(get_qpy_version(1), 1)


class TestGetSSVersion(IBMTestCase):
    """Test for getter of SSV version."""

    def test_no_highest_value(self):
        """Test with unset highest value."""
        self.assertEqual(get_ssv_version(), SSV)

    def test_highest_value(self):
        """Test with set highest value."""
        self.assertEqual(get_ssv_version(1), 1)


class TestValidateNoBoxes(IBMTestCase):
    """Tests for validate_no_boxes function."""

    def test_valid_circuit_no_boxes(self):
        """Test that a circuit without boxes passes validation."""
        circuit = QuantumCircuit(2, 2)
        circuit.h(0)
        circuit.cx(0, 1)
        circuit.measure_all()

        # Should not raise
        validate_no_boxes(circuit)

    def test_circuit_with_box_raises_error(self):
        """Test that a circuit with a BoxOp raises an error."""
        inner_circuit = QuantumCircuit(2)
        inner_circuit.h(0)
        inner_circuit.cx(0, 1)

        circuit = QuantumCircuit(2, 2)
        circuit.append(BoxOp(inner_circuit), [0, 1])
        circuit.measure_all()

        with self.assertRaisesRegex(IBMInputValueError, "not supported"):
            validate_no_boxes(circuit)
