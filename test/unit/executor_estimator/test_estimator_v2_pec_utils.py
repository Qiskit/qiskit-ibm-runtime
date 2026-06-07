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

"""Unit tests for EstimatorV2 PEC helper functions."""

import unittest

import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import PauliLindbladMap
from samplomatic import InjectNoise

from qiskit_ibm_runtime.executor_estimator.pec_utils import calculate_gamma


class TestCalculateGamma(unittest.TestCase):
    """Tests for calculate_gamma function."""

    def test_calculates_gamma_for_single_noisy_gate(self):
        """Test gamma calculation for a circuit with a single noisy two-qubit gate."""
        # Create a simple circuit with one two-qubit gate annotated with noise
        circuit = QuantumCircuit(2)
        with circuit.box(annotations=[InjectNoise(ref="layer_0")]):
            circuit.h(0)
            circuit.cx(0, 1)

        # Create a two-qubit noise model with known gamma
        noise_model = PauliLindbladMap.from_sparse_list(
            [("ZX", [0, 1], 0.1), ("XZ", [0, 1], 0.1)], num_qubits=2
        )
        noise_model_mapping = {"layer_0": noise_model}

        noise_factor = 1.0
        result = calculate_gamma(circuit, noise_model_mapping, noise_factor)

        # Expected gamma is the gamma of the noise model
        expected_gamma = noise_model.inverse().gamma()
        self.assertAlmostEqual(result, expected_gamma)

    def test_calculates_gamma_for_multiple_noisy_gates(self):
        """Test gamma calculation for a circuit with multiple noisy gates."""
        # Create a circuit with multiple gates
        circuit = QuantumCircuit(3)
        with circuit.box(annotations=[InjectNoise(ref="layer_0")]):
            circuit.h(0)
            circuit.cx(0, 1)
        with circuit.box(annotations=[InjectNoise(ref="layer_1")]):
            circuit.cx(1, 2)

        # Create noise models
        noise_model_0 = PauliLindbladMap.from_sparse_list([("XX", [0, 1], 0.1)], num_qubits=3)
        noise_model_1 = PauliLindbladMap.from_sparse_list(
            [("XY", [1, 2], 0.2), ("ZX", [1, 2], 0.15)], num_qubits=3
        )
        noise_model_mapping = {"layer_0": noise_model_0, "layer_1": noise_model_1}

        noise_factor = 1.0
        result = calculate_gamma(circuit, noise_model_mapping, noise_factor)

        # Expected gamma is the product of individual gammas
        expected_gamma = noise_model_0.inverse().gamma() * noise_model_1.inverse().gamma()
        self.assertAlmostEqual(result, expected_gamma)

    def test_calculates_gamma_for_repeated_noisy_gates(self):
        """Test gamma calculation for a circuit with multiple noisy gates."""
        # Create a circuit with multiple gates
        circuit = QuantumCircuit(2)
        with circuit.box(annotations=[InjectNoise(ref="layer_0")]):
            circuit.h(0)
            circuit.cx(0, 1)
        with circuit.box(annotations=[InjectNoise(ref="layer_0")]):
            circuit.h(0)
            circuit.cx(0, 1)

        # Create noise models
        noise_model_0 = PauliLindbladMap.from_sparse_list([("XX", [0, 1], 0.1)], num_qubits=2)
        noise_model_mapping = {"layer_0": noise_model_0}

        noise_factor = 1.0
        result = calculate_gamma(circuit, noise_model_mapping, noise_factor)

        # Expected gamma is the product of individual gammas
        expected_gamma = noise_model_0.inverse().gamma() * noise_model_0.inverse().gamma()
        self.assertAlmostEqual(result, expected_gamma)

    def test_gamma_equals_one_for_noiseless_circuit(self):
        """Test that gamma equals 1.0 for a circuit without noise annotations."""
        # Create a circuit with boxed gates but no InjectNoise annotations
        circuit = QuantumCircuit(2)
        with circuit.box():
            circuit.h(0)
            circuit.cx(0, 1)

        noise_model_mapping = {}
        noise_factor = 1.0

        result = calculate_gamma(circuit, noise_model_mapping, noise_factor)

        # Gamma should be 1.0 for noiseless circuit
        self.assertEqual(result, 1.0)

    def test_gamma_with_noise_factor_amplification(self):
        """Test gamma calculation with noise factor amplification."""
        # Create a circuit with one noisy two-qubit gate
        circuit = QuantumCircuit(2)
        with circuit.box(annotations=[InjectNoise(ref="layer_0")]):
            circuit.h(0)
            circuit.cx(0, 1)

        # Create a two-qubit noise model
        err_rate = 0.1
        noise_model = PauliLindbladMap.from_sparse_list(
            [("XX", [0, 1], err_rate), ("XZ", [0, 1], err_rate)], num_qubits=2
        )
        noise_model_mapping = {"layer_0": noise_model}

        # Test with different noise factors
        noise_factor = 2.0
        result = calculate_gamma(circuit, noise_model_mapping, noise_factor)

        # Expected gamma with amplified noise
        # gamma = w + abs(1-w), w = 0.5*(1+e^(-2*err))
        layer_gamma = 0.5 * (1 + np.exp(-2 * -noise_factor * err_rate)) + abs(
            1 - (0.5 * (1 + np.exp(-2 * -noise_factor * err_rate)))
        )
        expected_gamma = layer_gamma * layer_gamma
        self.assertAlmostEqual(result, expected_gamma)

    def test_gamma_with_mixed_noisy_and_noiseless_gates(self):
        """Test gamma calculation for circuit with both noisy and noiseless gates."""
        # Create a circuit with multiple gates, only some annotated
        circuit = QuantumCircuit(3)
        with circuit.box(annotations=[InjectNoise(ref="layer_0")]):
            circuit.h(0)  # This will be noisy
            circuit.cx(0, 1)
        with circuit.box():  # Box without InjectNoise annotation
            circuit.x(1)  # This will be noiseless
            circuit.cx(0, 2)
        with circuit.box(annotations=[InjectNoise(ref="layer_1")]):
            circuit.cx(1, 2)  # This will be noisy

        noise_model_0 = PauliLindbladMap.from_sparse_list([("XX", [0, 1], 0.1)], num_qubits=3)
        noise_model_1 = PauliLindbladMap.from_sparse_list(
            [("XZ", [1, 2], 0.15), ("XY", [1, 2], 0.2)], num_qubits=3
        )
        noise_model_mapping = {"layer_0": noise_model_0, "layer_1": noise_model_1}

        noise_factor = 1.0
        result = calculate_gamma(circuit, noise_model_mapping, noise_factor)

        # Expected gamma is product of only the noisy gates
        expected_gamma = noise_model_0.inverse().gamma() * noise_model_1.inverse().gamma()
        self.assertAlmostEqual(result, expected_gamma)

    def test_gamma_with_zero_noise_factor(self):
        """Test gamma calculation with zero noise factor."""
        # Create a circuit with one noisy two-qubit gate
        circuit = QuantumCircuit(2)
        with circuit.box(annotations=[InjectNoise(ref="layer_0")]):
            circuit.h(0)
            circuit.cx(0, 1)

        noise_model = PauliLindbladMap.from_sparse_list(
            [("IX", [0, 1], 0.1), ("XI", [0, 1], 0.1)], num_qubits=2
        )
        noise_model_mapping = {"layer_0": noise_model}

        # With zero noise factor, the noise is effectively removed
        noise_factor = 0.0
        result = calculate_gamma(circuit, noise_model_mapping, noise_factor)

        # Gamma should be 1.0 when noise is scaled to zero
        self.assertAlmostEqual(result, 1.0)
