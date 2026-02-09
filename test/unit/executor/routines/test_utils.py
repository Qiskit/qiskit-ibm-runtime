# This code is part of Qiskit.
#
# (C) Copyright IBM 2025.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Tests for executor-based SamplerV2 utility functions."""

import unittest
import numpy as np

from qiskit import QuantumCircuit
from qiskit.circuit import Parameter, BoxOp
from qiskit.primitives.containers.sampler_pub import SamplerPub

from qiskit_ibm_runtime.exceptions import IBMInputValueError
from qiskit_ibm_runtime.executor.routines.utils import (
    validate_no_boxes,
    pubs_to_quantum_program,
)
from qiskit_ibm_runtime.quantum_program import QuantumProgram
from qiskit_ibm_runtime.quantum_program.quantum_program import CircuitItem


class TestValidateNoBoxes(unittest.TestCase):
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

        with self.assertRaises(IBMInputValueError) as context:
            validate_no_boxes(circuit)

        self.assertIn("BoxOp", str(context.exception))
        self.assertIn("not supported", str(context.exception))


class TestPubsToQuantumProgram(unittest.TestCase):
    """Tests for pubs_to_quantum_program function."""

    def test_single_pub_no_parameters(self):
        """Test conversion of a single pub without parameters."""
        circuit = QuantumCircuit(2, 2)
        circuit.h(0)
        circuit.cx(0, 1)
        circuit.measure_all()

        pub = SamplerPub.coerce(circuit, shots=1024)
        program = pubs_to_quantum_program([pub])

        self.assertIsInstance(program, QuantumProgram)
        self.assertEqual(program.shots, 1024)
        self.assertEqual(len(program.items), 1)
        self.assertIsInstance(program.items[0], CircuitItem)
        self.assertEqual(program.items[0].circuit, circuit)

    def test_single_pub_with_parameters(self):
        """Test conversion of a single pub with parameters."""
        theta = Parameter("θ")
        circuit = QuantumCircuit(1, 1)
        circuit.rx(theta, 0)
        circuit.measure_all()

        param_values = np.array([[0.1], [0.2], [0.3]])
        pub = SamplerPub.coerce((circuit, param_values), shots=2048)
        program = pubs_to_quantum_program([pub])

        self.assertEqual(program.shots, 2048)
        self.assertEqual(len(program.items), 1)
        self.assertIsInstance(program.items[0], CircuitItem)
        np.testing.assert_array_equal(program.items[0].circuit_arguments, param_values)

    def test_multiple_pubs(self):
        """Test conversion of multiple pubs."""
        circuit1 = QuantumCircuit(2, 2)
        circuit1.h(0)
        circuit1.measure_all()

        circuit2 = QuantumCircuit(3, 3)
        circuit2.h([0, 1, 2])
        circuit2.measure_all()

        pubs = [
            SamplerPub.coerce(circuit1, shots=1024),
            SamplerPub.coerce(circuit2, shots=1024),
        ]
        program = pubs_to_quantum_program(pubs)

        self.assertEqual(program.shots, 1024)
        self.assertEqual(len(program.items), 2)
        self.assertEqual(program.items[0].circuit, circuit1)
        self.assertEqual(program.items[1].circuit, circuit2)

    def test_default_shots(self):
        """Test that default shots are used when not specified in pub."""
        circuit = QuantumCircuit(1, 1)
        circuit.h(0)
        circuit.measure_all()

        pub = SamplerPub.coerce(circuit)  # No shots specified
        program = pubs_to_quantum_program([pub], default_shots=4096)

        self.assertEqual(program.shots, 4096)

    def test_mismatched_shots_raises_error(self):
        """Test that mismatched shots across pubs raises an error."""
        circuit1 = QuantumCircuit(1, 1)
        circuit1.h(0)
        circuit1.measure_all()

        circuit2 = QuantumCircuit(1, 1)
        circuit2.x(0)
        circuit2.measure_all()

        pubs = [
            SamplerPub.coerce(circuit1, shots=1024),
            SamplerPub.coerce(circuit2, shots=2048),
        ]

        with self.assertRaises(IBMInputValueError) as context:
            pubs_to_quantum_program(pubs)

        self.assertIn("same number of shots", str(context.exception))

    def test_no_shots_specified_raises_error(self):
        """Test that missing shots raises an error."""
        circuit = QuantumCircuit(1, 1)
        circuit.h(0)
        circuit.measure_all()

        pub = SamplerPub.coerce(circuit)  # No shots

        with self.assertRaises(IBMInputValueError) as context:
            pubs_to_quantum_program([pub], default_shots=None)

        self.assertIn("Shots must be specified", str(context.exception))

    def test_empty_pubs_raises_error(self):
        """Test that empty pubs list raises an error."""
        with self.assertRaises(IBMInputValueError) as context:
            pubs_to_quantum_program([])

        self.assertIn("At least one pub", str(context.exception))

    def test_pub_with_box_raises_error(self):
        """Test that a pub with a BoxOp raises an error."""
        inner_circuit = QuantumCircuit(2)
        inner_circuit.h(0)

        circuit = QuantumCircuit(2, 2)
        circuit.append(BoxOp(inner_circuit), [0, 1])
        circuit.measure_all()

        pub = SamplerPub.coerce(circuit, shots=1024)

        with self.assertRaises(IBMInputValueError) as context:
            pubs_to_quantum_program([pub])

        self.assertIn("BoxOp", str(context.exception))