# This code is part of Qiskit.
#
# (C) Copyright IBM 2026.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Tests the ``CircuitItem`` class."""

import numpy as np

from qiskit.circuit import QuantumCircuit, Parameter

from qiskit_ibm_runtime.quantum_program.quantum_program import CircuitItem


from ...ibm_test_case import IBMTestCase


class TestCircuitItem(IBMTestCase):
    """Tests the ``CircuitItem`` class."""

    def test_circuit_item(self):
        """Test ``CircuitItem`` for a valid input."""
        circuit = QuantumCircuit(1)
        circuit.rx(Parameter("p"), 0)

        circuit_arguments = np.array([[3], [4], [5]])
        expected_shape = (3,)
        chunk_size = 6

        circuit_item = CircuitItem(
            circuit, circuit_arguments=circuit_arguments, chunk_size=chunk_size
        )
        self.assertEqual(circuit_item.circuit, circuit)
        self.assertTrue(np.array_equal(circuit_item.circuit_arguments, circuit_arguments))
        self.assertEqual(circuit_item.chunk_size, chunk_size)
        self.assertEqual(circuit_item.shape, expected_shape)

    def test_circuit_item_no_params(self):
        """Test ``CircuitItem`` when there are no parameters."""
        circuit = QuantumCircuit(1)

        expected_circuit_arguments = np.array([])
        expected_shape = ()

        circuit_item = CircuitItem(circuit)
        self.assertEqual(circuit_item.circuit, circuit)
        self.assertTrue(np.array_equal(circuit_item.circuit_arguments, expected_circuit_arguments))
        self.assertEqual(circuit_item.chunk_size, None)
        self.assertEqual(circuit_item.shape, expected_shape)

    def test_circuit_item_num_params_doesnt_match_circuit_arguments(self):
        """Test that ``CircuitItem`` raises an error if the number of circuit parameters
        doesn't match the shape of the circuit arguments."""
        circuit = QuantumCircuit(1)
        circuit.rx(Parameter("p"), 0)

        circuit_arguments = np.array([[3, 10], [4, 11], [5, 12]])
        with self.assertRaisesRegex(ValueError, "match the number of parameters"):
            CircuitItem(circuit, circuit_arguments=circuit_arguments)

    def test_circuit_item_no_circuit_arguments_for_parametric_circuit(self):
        """Test that ``CircuitItem`` raises an error if the circuit has parameters
        but the ``circuit_arguments`` parameter is unset."""
        circuit = QuantumCircuit(1)
        circuit.rx(Parameter("p"), 0)

        with self.assertRaisesRegex(ValueError, "no 'circuit_arguments'"):
            CircuitItem(circuit)
