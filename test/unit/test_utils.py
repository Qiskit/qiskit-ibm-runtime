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

"""Tests for the methods utils.utils file."""

from qiskit import QuantumCircuit

from qiskit_ibm_runtime.exceptions import RuntimePrimitiveInputInvalidError
from qiskit_ibm_runtime.utils.utils import validate_circuit
from ..ibm_test_case import IBMTestCase


class TestUtils(IBMTestCase):
    """Tests for the methods in the utils.utils file."""

    def test_validate_circuit_valid_circuit(self):
        """Test validate_circuit method with a valid circuit."""
        circuit = QuantumCircuit(2)
        circuit.h(0)
        circuit.cx(0, 1)
        circuit.measure_all()
        try:
            validate_circuit(circuit, RuntimePrimitiveInputInvalidError)
        except RuntimePrimitiveInputInvalidError:
            self.fail("should not raise RuntimePrimitiveInputInvalidError")

    def test_validate_circuit_invalid_circuit(self):
        """Test validate_circuit method with a circuit missing measurements."""
        circuit = QuantumCircuit(2)
        circuit.h(0)
        circuit.cnot(0, 1)
        with self.assertRaises(RuntimePrimitiveInputInvalidError):
            validate_circuit(circuit, RuntimePrimitiveInputInvalidError)
