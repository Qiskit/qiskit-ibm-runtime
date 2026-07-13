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

"""Unit tests for EstimatorV2 PEA helper functions."""

import math
import unittest
from typing import Any, cast

import numpy as np
from ddt import ddt
from qiskit.circuit import Parameter, QuantumCircuit
from qiskit.primitives.containers.estimator_pub import EstimatorPub
from qiskit.quantum_info import PauliLindbladMap, SparsePauliOp
from samplomatic import InjectNoise
from samplomatic.utils import get_annotation

from qiskit_ibm_runtime.exceptions import IBMInputValueError
from qiskit_ibm_runtime.executor_estimator.prepare_pea import prepare_pea
from qiskit_ibm_runtime.executor_estimator.utils import find_unique_layers
from qiskit_ibm_runtime.options_models.measure_noise_learning_options import (
    MeasureNoiseLearningOptions,
)
from qiskit_ibm_runtime.options_models.twirling_options import TwirlingOptions
from qiskit_ibm_runtime.options_models.zne_options import ZneOptions
from qiskit_ibm_runtime.quantum_program import QuantumProgram
from qiskit_ibm_runtime.quantum_program.quantum_program import SamplexItem


@ddt
class TestPreparePeaFunction(unittest.TestCase):
    """Tests for the prepare_pea function."""

    def test_prepare_pea_basic(self):
        """Test prepare_pea with basic noise factors and noise model."""
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

        noise_factors = [1, 1.5, 2, 2.5, 3]
        zne_options = ZneOptions()
        zne_options.amplifier = "pea"
        zne_options.noise_factors = noise_factors

        twirling_options = TwirlingOptions()
        twirling_options.enable_gates = True
        twirling_options.enable_measure = True

        shots = 1024
        quantum_program = prepare_pea(
            [pub], twirling_options, shots, zne_options, noise_model_mapping
        )

        self.assertIsInstance(quantum_program, QuantumProgram)
        self.assertEqual(quantum_program.shots, 64)
        self.assertEqual(quantum_program._semantic_role, "estimator_v2")
        self.assertEqual(len(quantum_program.items), 1)

        item = cast("SamplexItem", quantum_program.items[0])
        self.assertIsInstance(item, SamplexItem)
        # Check samplex shape
        auto_num_rand = math.ceil(shots / (max(64, math.ceil(shots / 32))))
        # The expected shape is (num_randomizations, num_noise_factors, bases * num_param_sets)
        expected_shape = (auto_num_rand, len(noise_factors), 1)
        self.assertEqual(item.shape, expected_shape)

        # Check that samplex_arguments contains pauli_lindblad_maps
        self.assertIn(f"pauli_lindblad_maps.{noise_layer_ref}", item.samplex_arguments)
        self.assertEqual(
            item.samplex_arguments[f"pauli_lindblad_maps.{noise_layer_ref}"],
            noise_model_mapping[noise_layer_ref],
        )

        # Check that samplex_arguments contains noise_scales for the layer
        self.assertIn(f"noise_scales.{noise_layer_ref}", item.samplex_arguments)
        # noise_scales = noise_factors - 1
        expected_noise_scales = np.array([[factor - 1] for factor in noise_factors])
        self.assertTrue(
            np.all(
                item.samplex_arguments[f"noise_scales.{noise_layer_ref}"] == expected_noise_scales
            )
        )

        # Check passthrough_data contains pea_noise_factors
        passthrough = cast("dict[str, Any]", quantum_program.passthrough_data)
        self.assertIn("pea_noise_factors", passthrough["post_processor"])
        self.assertTrue(
            np.array_equal(
                np.array(passthrough["post_processor"]["pea_noise_factors"]),
                np.array(noise_factors),
            )
        )

    def test_prepare_pea_multiple_pubs(self):
        """Test prepare_pea with multiple pubs and different noise models."""
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

        noise_factors = [1, 1.5, 2, 2.5, 3]
        zne_options = ZneOptions()
        zne_options.amplifier = "pea"
        zne_options.noise_factors = noise_factors

        twirling_options = TwirlingOptions()
        twirling_options.enable_gates = True
        twirling_options.enable_measure = True

        shots = 2048
        quantum_program = prepare_pea(
            [pub1, pub2], twirling_options, shots, zne_options, noise_model_mapping
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
        expected_noise_scales = np.array([[factor - 1] for factor in noise_factors])
        self.assertTrue(
            np.all(
                item1.samplex_arguments[f"noise_scales.{noise_layer_refs[0]}"]
                == expected_noise_scales
            )
        )

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
        self.assertTrue(
            np.all(
                item2.samplex_arguments[f"noise_scales.{noise_layer_refs[1]}"]
                == expected_noise_scales
            )
        )
        self.assertTrue(
            np.all(
                item2.samplex_arguments[f"noise_scales.{noise_layer_refs[2]}"]
                == expected_noise_scales
            )
        )

        # Check passthrough_data contains pec_gammas for both pubs
        passthrough = cast("dict[str, Any]", quantum_program.passthrough_data)
        self.assertIn("pea_noise_factors", passthrough["post_processor"])
        self.assertTrue(
            np.array_equal(
                np.array(passthrough["post_processor"]["pea_noise_factors"]),
                np.array(noise_factors),
            )
        )

    def test_prepare_pea_raises_error_with_empty_noise_model_mapping(self):
        """Test that prepare_pea raises error when noise_model_mapping is empty."""
        circuit = QuantumCircuit(2)
        circuit.h(0)
        circuit.cx(0, 1)

        observable = SparsePauliOp.from_list([("ZZ", 1)])
        pub = EstimatorPub.coerce((circuit, observable))

        noise_factors = [1, 1.5, 2, 2.5, 3]
        zne_options = ZneOptions()
        zne_options.amplifier = "pea"
        zne_options.noise_factors = noise_factors

        twirling_options = TwirlingOptions()
        twirling_options.enable_gates = True
        twirling_options.enable_measure = True

        with self.assertRaises(IBMInputValueError) as context:
            prepare_pea([pub], twirling_options, 1024, zne_options, {})

        self.assertIn("noise_model_mapping", str(context.exception))

    def test_prepare_pea_raises_error_with_missing_noise_model_key(self):
        """Test that prepare_pea raises error when noise_model_mapping is missing a noise model."""
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
        noise_layer_ref_pub1 = ""
        for layer in layers:
            if annot := get_annotation(layer.operation, InjectNoise):
                noise_layer_ref_pub1 = annot.ref

        noise_model_mapping = {noise_layer_ref_pub1: noise_model}

        noise_factors = [1, 1.5, 2, 2.5, 3]
        zne_options = ZneOptions()
        zne_options.amplifier = "pea"
        zne_options.noise_factors = noise_factors

        twirling_options = TwirlingOptions()
        twirling_options.enable_gates = True
        twirling_options.enable_measure = True

        with self.assertRaises(IBMInputValueError) as context:
            prepare_pea([pub1, pub2], twirling_options, 1024, zne_options, noise_model_mapping)

        self.assertIn("noise_model_mapping", str(context.exception))

    def test_prepare_pea_with_measure_noise_learning(self):
        """Test prepare_pea with measure noise learning (TREX)."""
        circuit = QuantumCircuit(2)
        circuit.h(0)
        circuit.cx(0, 1)

        observable = SparsePauliOp.from_list([("ZZ", 1)])
        pub = EstimatorPub.coerce((circuit, observable))

        noise_model = PauliLindbladMap.from_sparse_list([("XX", [0, 1], 0.1)], num_qubits=2)

        twirling_options = TwirlingOptions()
        twirling_options.enable_gates = True
        twirling_options.enable_measure = True

        # find layers first to extract the layers ref
        layers = find_unique_layers([pub], twirling_options, inject_noise=True)
        noise_layer_ref = ""
        for layer in layers:
            if annot := get_annotation(layer.operation, InjectNoise):
                noise_layer_ref = annot.ref

        noise_model_mapping = {noise_layer_ref: noise_model}

        noise_factors = [1, 1.5, 2, 2.5, 3]
        zne_options = ZneOptions()
        zne_options.amplifier = "pea"
        zne_options.noise_factors = noise_factors

        measure_noise_learning = MeasureNoiseLearningOptions()
        measure_noise_learning.num_randomizations = 16

        quantum_program = prepare_pea(
            [pub],
            twirling_options,
            1024,
            zne_options,
            noise_model_mapping,
            measure_noise_learning,
        )

        # Should have 2 items: 1 for pub + 1 TREX calibration
        self.assertEqual(len(quantum_program.items), 2)

        # Check first item has PEA arguments
        item = cast("SamplexItem", quantum_program.items[0])
        self.assertIn(f"pauli_lindblad_maps.{noise_layer_ref}", item.samplex_arguments)
        self.assertEqual(
            item.samplex_arguments[f"pauli_lindblad_maps.{noise_layer_ref}"],
            noise_model_mapping[noise_layer_ref],
        )
        self.assertIn(f"noise_scales.{noise_layer_ref}", item.samplex_arguments)
        expected_noise_scales = np.array([[factor - 1] for factor in noise_factors])
        self.assertTrue(
            np.all(
                item.samplex_arguments[f"noise_scales.{noise_layer_ref}"] == expected_noise_scales
            )
        )

        # Check passthrough data
        passthrough = cast("dict[str, Any]", quantum_program.passthrough_data)
        self.assertEqual(passthrough["post_processor"]["measure_mitigation"], "True")
        self.assertIn("pea_noise_factors", passthrough["post_processor"])
        self.assertTrue(
            np.array_equal(
                np.array(passthrough["post_processor"]["pea_noise_factors"]),
                np.array(noise_factors),
            )
        )

    def test_prepare_pea_with_parameters(self):
        """Test prepare_pea with a pub containing parameters and validate final shape."""
        # Create a parameterized circuit with rz gates (supported by samplomatic)
        circuit = QuantumCircuit(2)
        theta = Parameter("theta")
        phi = Parameter("phi")
        circuit.h(0)
        circuit.rz(theta, 0)
        circuit.rz(phi, 1)
        circuit.cx(0, 1)

        observable = SparsePauliOp.from_list([("ZZ", 1)])

        # Create parameter values with shape (3, 2) - 3 sets of 2 parameters
        parameter_values = np.array([[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]])

        pub = EstimatorPub.coerce((circuit, observable, parameter_values))

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

        noise_factors = [1, 1.5, 2, 2.5, 3]
        zne_options = ZneOptions()
        zne_options.amplifier = "pea"
        zne_options.noise_factors = noise_factors

        twirling_options = TwirlingOptions()
        twirling_options.enable_gates = True
        twirling_options.enable_measure = True

        shots = 1024
        quantum_program = prepare_pea(
            [pub], twirling_options, shots, zne_options, noise_model_mapping
        )

        self.assertIsInstance(quantum_program, QuantumProgram)
        self.assertEqual(len(quantum_program.items), 1)

        item = cast("SamplexItem", quantum_program.items[0])
        self.assertIsInstance(item, SamplexItem)

        # Check the shape of the program item
        # The expected shape is (num_randomizations, num_noise_factors, bases * num_param_sets)
        # num_randomizations is calculated automatically based on shots
        auto_num_rand = math.ceil(shots / (max(64, math.ceil(shots / 32))))
        num_param_sets = parameter_values.shape[0]  # 3
        num_observables = 1  # Single observable
        num_noise_factors = len(noise_factors)  # 5

        expected_shape = (auto_num_rand, num_noise_factors, num_param_sets * num_observables)
        self.assertEqual(
            item.shape,
            expected_shape,
            f"Expected shape {expected_shape}, but got {item.shape}",
        )

        # Verify samplex_arguments contains the parameter values with correct shape
        # Parameters should be expanded to be broadcastable with noise scales
        self.assertIn("parameter_values", item.samplex_arguments)
        param_values_in_samplex = item.samplex_arguments["parameter_values"]
        # Shape should be (num_param_sets, 1, num_parameters) after expansion
        expected_param_shape = (1, num_param_sets, circuit.num_parameters)
        self.assertEqual(
            param_values_in_samplex.shape,
            expected_param_shape,
            f"Expected parameter shape {expected_param_shape}, but got "
            f"{param_values_in_samplex.shape}",
        )

        # Check that samplex_arguments contains noise-related data
        self.assertIn(f"pauli_lindblad_maps.{noise_layer_ref}", item.samplex_arguments)
        self.assertIn(f"noise_scales.{noise_layer_ref}", item.samplex_arguments)

        # Verify noise_scales are correct (noise_factors - 1)
        expected_noise_scales = np.array([[factor - 1] for factor in noise_factors])
        self.assertTrue(
            np.all(
                item.samplex_arguments[f"noise_scales.{noise_layer_ref}"] == expected_noise_scales
            )
        )

        # Check passthrough_data contains correct information
        passthrough = cast("dict[str, Any]", quantum_program.passthrough_data)
        self.assertIn("pea_noise_factors", passthrough["post_processor"])
        self.assertTrue(
            np.array_equal(
                np.array(passthrough["post_processor"]["pea_noise_factors"]),
                np.array(noise_factors),
            )
        )
        self.assertIn("param_shapes", passthrough["post_processor"])
        self.assertEqual(
            passthrough["post_processor"]["param_shapes"][0], pub.parameter_values.shape
        )
