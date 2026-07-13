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

import math
import unittest
from typing import Any, cast

import numpy as np
from ddt import ddt
from qiskit import QuantumCircuit
from qiskit.primitives.containers.estimator_pub import EstimatorPub
from qiskit.quantum_info import PauliLindbladMap, SparsePauliOp
from samplomatic import InjectNoise
from samplomatic.utils import get_annotation

from qiskit_ibm_runtime.exceptions import IBMInputValueError
from qiskit_ibm_runtime.executor_estimator.pec.prepare_pec import prepare_pec
from qiskit_ibm_runtime.executor_estimator.pec.utils import calculate_gamma
from qiskit_ibm_runtime.executor_estimator.utils import find_unique_layers
from qiskit_ibm_runtime.options_models.measure_noise_learning_options import (
    MeasureNoiseLearningOptions,
)
from qiskit_ibm_runtime.options_models.pec_options import PecOptions
from qiskit_ibm_runtime.options_models.twirling_options import TwirlingOptions
from qiskit_ibm_runtime.quantum_program import QuantumProgram
from qiskit_ibm_runtime.quantum_program.quantum_program import SamplexItem


class TestCalculateGamma(unittest.TestCase):
    """Tests for calculate_gamma function."""

    def test_calculates_gamma_for_single_noisy_gate(self):
        """Test gamma calculation for a circuit with a single noisy two-qubit gate."""
        # Create a simple circuit with one two-qubit gate annotated with noise
        circuit = QuantumCircuit(2)
        with circuit.box(annotations=[InjectNoise(ref="layer_0", site="after")]):
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
        with circuit.box(annotations=[InjectNoise(ref="layer_0", site="after")]):
            circuit.h(0)
            circuit.cx(0, 1)
        with circuit.box(annotations=[InjectNoise(ref="layer_1", site="after")]):
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
        with circuit.box(annotations=[InjectNoise(ref="layer_0", site="after")]):
            circuit.h(0)
            circuit.cx(0, 1)
        with circuit.box(annotations=[InjectNoise(ref="layer_0", site="after")]):
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
        with circuit.box(annotations=[InjectNoise(ref="layer_0", site="after")]):
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
        with circuit.box(annotations=[InjectNoise(ref="layer_0", site="after")]):
            circuit.h(0)  # This will be noisy
            circuit.cx(0, 1)
        with circuit.box():  # Box without InjectNoise annotation
            circuit.x(1)  # This will be noiseless
            circuit.cx(0, 2)
        with circuit.box(annotations=[InjectNoise(ref="layer_1", site="after")]):
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
        with circuit.box(annotations=[InjectNoise(ref="layer_0", site="after")]):
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


@ddt
class TestPreparePecFunction(unittest.TestCase):
    """Tests for the prepare_pec function."""

    def test_prepare_pec_basic(self):
        """Test prepare_pec with basic PEC options and noise model."""
        circuit = QuantumCircuit(2)
        circuit.h(0)
        circuit.cx(0, 1)

        observable = SparsePauliOp.from_list([("ZZ", 1)])
        pub = EstimatorPub.coerce((circuit, observable))

        # Create a simple noise model
        noise_model = PauliLindbladMap.from_sparse_list(
            [("XX", [0, 1], 0.1), ("ZZ", [0, 1], 0.05)], num_qubits=2
        )
        # find layers first to extract the layers ref
        layers = find_unique_layers([pub], TwirlingOptions(), inject_noise=True)
        noise_layer_ref = ""
        for layer in layers:
            if annot := get_annotation(layer.operation, InjectNoise):
                noise_layer_ref = annot.ref

        noise_model_mapping = {noise_layer_ref: noise_model}

        pec_options = PecOptions()
        pec_options.noise_gain = 0.5

        twirling_options = TwirlingOptions()
        twirling_options.enable_gates = True
        twirling_options.enable_measure = True

        shots = 1024
        quantum_program = prepare_pec(
            [pub], twirling_options, shots, pec_options, noise_model_mapping
        )

        self.assertIsInstance(quantum_program, QuantumProgram)
        self.assertEqual(quantum_program.shots, 64)
        self.assertEqual(quantum_program._semantic_role, "estimator_v2")
        self.assertEqual(len(quantum_program.items), 1)

        item = cast("SamplexItem", quantum_program.items[0])
        self.assertIsInstance(item, SamplexItem)

        # Check that samplex_arguments contains pauli_lindblad_maps
        self.assertIn(f"pauli_lindblad_maps.{noise_layer_ref}", item.samplex_arguments)
        self.assertEqual(
            item.samplex_arguments[f"pauli_lindblad_maps.{noise_layer_ref}"],
            noise_model_mapping[noise_layer_ref],
        )

        # Check that samplex_arguments contains noise_scales for the layer
        self.assertIn(f"noise_scales.{noise_layer_ref}", item.samplex_arguments)
        # noise_gain = 0.5, so noise_factor = 0.5 - 1 = -0.5
        expected_noise_factor = pec_options.noise_gain - 1
        self.assertEqual(
            item.samplex_arguments[f"noise_scales.{noise_layer_ref}"], expected_noise_factor
        )

        # Check passthrough_data contains pec_gammas
        passthrough = cast("dict[str, Any]", quantum_program.passthrough_data)
        self.assertIn("pec_gammas", passthrough["post_processor"])
        self.assertEqual(len(passthrough["post_processor"]["pec_gammas"]), 1)
        self.assertIsInstance(passthrough["post_processor"]["pec_gammas"][0], float)
        expected_gamma = float(np.exp(2 * pec_options.noise_gain * (0.1 + 0.05)))
        self.assertAlmostEqual(passthrough["post_processor"]["pec_gammas"][0], expected_gamma)
        # check number of randomizations
        overhead = expected_gamma**2
        expected_num_rands = math.ceil(overhead * (shots / 64))
        self.assertEqual(item.shape[0], expected_num_rands)

    def test_prepare_pec_multiple_pubs(self):
        """Test prepare_pec with multiple pubs and different noise models."""
        circuit1 = QuantumCircuit(2)
        circuit1.h(0)
        circuit1.cx(0, 1)

        circuit2 = QuantumCircuit(3)
        circuit2.h(0)
        circuit2.cx(0, 1)
        circuit2.cx(1, 2)

        observable1 = SparsePauliOp.from_list([("ZZ", 1)])
        observable2 = SparsePauliOp.from_list([("ZZZ", 1)])

        pub1 = EstimatorPub.coerce((circuit1, observable1))
        pub2 = EstimatorPub.coerce((circuit2, observable2))

        # Create different noise models for each pub
        noise_model_1 = PauliLindbladMap.from_sparse_list([("XX", [0, 1], 0.1)], num_qubits=2)
        noise_model_2a = PauliLindbladMap.from_sparse_list([("XY", [0, 1], 0.15)], num_qubits=2)
        noise_model_2b = PauliLindbladMap.from_sparse_list([("ZX", [1, 2], 0.2)], num_qubits=3)

        # find layers first to extract the layers ref
        layers = find_unique_layers([pub1, pub2], TwirlingOptions(), inject_noise=True)
        noise_layer_refs = []
        for layer in layers:
            if annot := get_annotation(layer.operation, InjectNoise):
                noise_layer_refs.append(annot.ref)

        noise_model_mapping = {
            noise_layer_refs[0]: noise_model_1,
            noise_layer_refs[1]: noise_model_2a,
            noise_layer_refs[2]: noise_model_2b,
        }

        pec_options = PecOptions()
        pec_options.noise_gain = 0.3

        twirling_options = TwirlingOptions()
        twirling_options.enable_gates = True
        twirling_options.enable_measure = True

        shots = 2048
        quantum_program = prepare_pec(
            [pub1, pub2], twirling_options, shots, pec_options, noise_model_mapping
        )

        self.assertEqual(len(quantum_program.items), 2)

        # Check first item
        item1 = cast("SamplexItem", quantum_program.items[0])
        self.assertIn(f"pauli_lindblad_maps.{noise_layer_refs[0]}", item1.samplex_arguments)
        self.assertEqual(
            item1.samplex_arguments[f"pauli_lindblad_maps.{noise_layer_refs[0]}"],
            noise_model_mapping[noise_layer_refs[0]],
        )
        self.assertIn(f"noise_scales.{noise_layer_refs[0]}", item1.samplex_arguments)

        # Check second item
        item2 = cast("SamplexItem", quantum_program.items[1])
        self.assertIn(f"pauli_lindblad_maps.{noise_layer_refs[1]}", item2.samplex_arguments)
        self.assertIn(f"pauli_lindblad_maps.{noise_layer_refs[2]}", item2.samplex_arguments)
        self.assertEqual(
            item2.samplex_arguments[f"pauli_lindblad_maps.{noise_layer_refs[1]}"],
            noise_model_mapping[noise_layer_refs[1]],
        )
        self.assertEqual(
            item2.samplex_arguments[f"pauli_lindblad_maps.{noise_layer_refs[2]}"],
            noise_model_mapping[noise_layer_refs[2]],
        )
        self.assertIn(f"noise_scales.{noise_layer_refs[1]}", item2.samplex_arguments)
        self.assertIn(f"noise_scales.{noise_layer_refs[2]}", item2.samplex_arguments)

        # Check passthrough_data contains pec_gammas for both pubs
        passthrough = cast("dict[str, Any]", quantum_program.passthrough_data)
        self.assertIn("pec_gammas", passthrough["post_processor"])
        self.assertEqual(len(passthrough["post_processor"]["pec_gammas"]), 2)

    def test_prepare_pec_with_auto_noise_gain(self):
        """Test prepare_pec with auto noise_gain (defaults to 0)."""
        circuit = QuantumCircuit(2)
        circuit.h(0)
        circuit.cx(0, 1)

        observable = SparsePauliOp.from_list([("ZZ", 1)])
        pub = EstimatorPub.coerce((circuit, observable))

        err_rate = 0.7
        max_overhead = 10
        noise_model = PauliLindbladMap.from_sparse_list([("IX", [0, 1], err_rate)], num_qubits=2)
        # find layers first to extract the layers ref
        layers = find_unique_layers([pub], TwirlingOptions(), inject_noise=True)
        noise_layer_ref = ""
        for layer in layers:
            if annot := get_annotation(layer.operation, InjectNoise):
                noise_layer_ref = annot.ref

        noise_model_mapping = {noise_layer_ref: noise_model}

        pec_options = PecOptions()
        pec_options.noise_gain = "auto"  # Should default to 0
        pec_options.max_overhead = max_overhead

        twirling_options = TwirlingOptions()
        twirling_options.enable_gates = True
        twirling_options.enable_measure = True

        shots = 1024
        quantum_program = prepare_pec(
            [pub], twirling_options, shots, pec_options, noise_model_mapping
        )

        item = cast("SamplexItem", quantum_program.items[0])

        # With auto (defaulting to 0), noise_factor should be 0 - 1 = -1
        self.assertIn(f"noise_scales.{noise_layer_ref}", item.samplex_arguments)
        scaleless_gamma = float(np.exp(2 * err_rate))
        expected_noise_gain = -np.log(max_overhead) / np.log(scaleless_gamma**2)
        self.assertEqual(
            item.samplex_arguments[f"noise_scales.{noise_layer_ref}"], expected_noise_gain
        )

    def test_prepare_pec_raises_error_with_empty_noise_model_mapping(self):
        """Test that prepare_pec raises error when noise_model_mapping is empty."""
        circuit = QuantumCircuit(2)
        circuit.h(0)
        circuit.cx(0, 1)

        observable = SparsePauliOp.from_list([("ZZ", 1)])
        pub = EstimatorPub.coerce((circuit, observable))

        pec_options = PecOptions()
        pec_options.noise_gain = 0.5

        twirling_options = TwirlingOptions()
        twirling_options.enable_gates = True
        twirling_options.enable_measure = True

        with self.assertRaises(IBMInputValueError) as context:
            prepare_pec([pub], twirling_options, 1024, pec_options, {})

        self.assertIn("noise_model_mapping", str(context.exception))

    def test_prepare_pec_raises_error_with_missing_noise_model_key(self):
        """Test that prepare_pec raises error when noise_model_mapping is missing a noise model."""
        circuit1 = QuantumCircuit(2)
        circuit1.h(0)
        circuit1.cx(0, 1)

        circuit2 = QuantumCircuit(2)
        circuit2.h(0)
        circuit2.cz(0, 1)

        observable = SparsePauliOp.from_list([("ZZ", 1)])
        pub1 = EstimatorPub.coerce((circuit1, observable))
        pub2 = EstimatorPub.coerce((circuit2, observable))

        # Only provide noise model for one pub, but we have two pubs
        noise_model = PauliLindbladMap.from_sparse_list([("XX", [0, 1], 0.1)], num_qubits=2)
        # find layers first to extract the layers ref
        layers = find_unique_layers([pub1], TwirlingOptions(), inject_noise=True)
        noise_layer_ref = ""
        for layer in layers:
            if annot := get_annotation(layer.operation, InjectNoise):
                noise_layer_ref = annot.ref

        noise_model_mapping = {noise_layer_ref: noise_model}

        pec_options = PecOptions()
        pec_options.noise_gain = 0.5

        twirling_options = TwirlingOptions()
        twirling_options.enable_gates = True
        twirling_options.enable_measure = True

        with self.assertRaises(IBMInputValueError) as context:
            prepare_pec([pub1, pub2], twirling_options, 1024, pec_options, noise_model_mapping)

        self.assertIn("noise_model_mapping", str(context.exception))

    def test_prepare_pec_with_measure_noise_learning(self):
        """Test prepare_pec with measure noise learning (TREX)."""
        circuit = QuantumCircuit(2)
        circuit.h(0)
        circuit.cx(0, 1)

        observable = SparsePauliOp.from_list([("ZZ", 1)])
        pub = EstimatorPub.coerce((circuit, observable))

        noise_model = PauliLindbladMap.from_sparse_list([("XX", [0, 1], 0.1)], num_qubits=2)
        # find layers first to extract the layers ref
        layers = find_unique_layers([pub], TwirlingOptions(), inject_noise=True)
        noise_layer_ref = ""
        for layer in layers:
            if annot := get_annotation(layer.operation, InjectNoise):
                noise_layer_ref = annot.ref

        noise_model_mapping = {noise_layer_ref: noise_model}

        pec_options = PecOptions()
        pec_options.noise_gain = 0.5

        measure_noise_learning = MeasureNoiseLearningOptions()
        measure_noise_learning.num_randomizations = 16

        twirling_options = TwirlingOptions()
        twirling_options.enable_gates = True
        twirling_options.enable_measure = True

        quantum_program = prepare_pec(
            [pub], twirling_options, 1024, pec_options, noise_model_mapping, measure_noise_learning
        )

        # Should have 2 items: 1 for pub + 1 TREX calibration
        self.assertEqual(len(quantum_program.items), 2)

        # Check first item has PEC arguments
        item = cast("SamplexItem", quantum_program.items[0])
        self.assertIn(f"pauli_lindblad_maps.{noise_layer_ref}", item.samplex_arguments)
        self.assertEqual(
            item.samplex_arguments[f"pauli_lindblad_maps.{noise_layer_ref}"],
            noise_model_mapping[noise_layer_ref],
        )
        self.assertIn(f"noise_scales.{noise_layer_ref}", item.samplex_arguments)
        expected_noise_factor = pec_options.noise_gain - 1
        self.assertEqual(
            item.samplex_arguments[f"noise_scales.{noise_layer_ref}"], expected_noise_factor
        )

        # Check passthrough data
        passthrough = cast("dict[str, Any]", quantum_program.passthrough_data)
        self.assertEqual(passthrough["post_processor"]["measure_mitigation"], "True")
        self.assertIn("pec_gammas", passthrough["post_processor"])
