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

"""Tests for executor-based SamplerV2 utility functions."""

import unittest

from qiskit import QuantumCircuit
from qiskit.circuit import BoxOp
from qiskit.primitives.containers.sampler_pub import SamplerPub

from qiskit_ibm_runtime.exceptions import IBMInputValueError
from qiskit_ibm_runtime.executor.routines.utils import (
    validate_no_boxes,
    extract_shots_from_pubs,
)


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


class TestExtractShotsFromPubs(unittest.TestCase):
    """Tests for extract_shots_from_pubs function."""

    def test_single_pub_with_shots(self):
        """Test extracting shots from a single pub with shots specified."""
        circuit = QuantumCircuit(2, 2)
        circuit.h(0)
        circuit.cx(0, 1)
        circuit.measure_all()

        pub = SamplerPub.coerce(circuit, shots=1024)
        shots = extract_shots_from_pubs([pub])

        self.assertEqual(shots, 1024)

    def test_single_pub_with_default_shots(self):
        """Test extracting shots using default_shots when pub doesn't specify."""
        circuit = QuantumCircuit(2, 2)
        circuit.h(0)
        circuit.measure_all()

        pub = SamplerPub.coerce(circuit)  # No shots specified
        shots = extract_shots_from_pubs([pub], default_shots=2048)

        self.assertEqual(shots, 2048)

    def test_multiple_pubs_same_shots(self):
        """Test extracting shots from multiple pubs with same shots value."""
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
        shots = extract_shots_from_pubs(pubs)

        self.assertEqual(shots, 1024)

    def test_multiple_pubs_mixed_shots_sources(self):
        """Test multiple pubs where some use default_shots and some specify shots."""
        circuit1 = QuantumCircuit(1, 1)
        circuit1.h(0)
        circuit1.measure_all()

        circuit2 = QuantumCircuit(1, 1)
        circuit2.x(0)
        circuit2.measure_all()

        pubs = [
            SamplerPub.coerce(circuit1, shots=512),
            SamplerPub.coerce(circuit2),  # Will use default_shots
        ]
        shots = extract_shots_from_pubs(pubs, default_shots=512)

        self.assertEqual(shots, 512)

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
            extract_shots_from_pubs(pubs)

        self.assertIn("same number of shots", str(context.exception))
        self.assertIn("1024", str(context.exception))
        self.assertIn("2048", str(context.exception))

    def test_no_shots_specified_raises_error(self):
        """Test that missing shots raises an error."""
        circuit = QuantumCircuit(1, 1)
        circuit.h(0)
        circuit.measure_all()

        pub = SamplerPub.coerce(circuit)  # No shots

        with self.assertRaises(IBMInputValueError) as context:
            extract_shots_from_pubs([pub], default_shots=None)

        self.assertIn("Shots must be specified", str(context.exception))

    def test_empty_pubs_raises_error(self):
        """Test that empty pubs list raises an error."""
        with self.assertRaises(IBMInputValueError) as context:
            extract_shots_from_pubs([])

        self.assertIn("At least one pub", str(context.exception))

    def test_pub_shots_overrides_default(self):
        """Test that pub.shots takes precedence over default_shots."""
        circuit = QuantumCircuit(1, 1)
        circuit.h(0)
        circuit.measure_all()

        pub = SamplerPub.coerce(circuit, shots=1024)
        shots = extract_shots_from_pubs([pub], default_shots=2048)

        # Should use pub.shots (1024), not default_shots (2048)
        self.assertEqual(shots, 1024)
