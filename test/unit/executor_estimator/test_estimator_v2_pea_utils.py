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
from qiskit import QuantumCircuit
from qiskit.primitives.containers.estimator_pub import EstimatorPub
from qiskit.quantum_info import PauliLindbladMap, SparsePauliOp

from qiskit_ibm_runtime.exceptions import IBMInputValueError
from qiskit_ibm_runtime.executor_estimator.pea_utils import prepare_pea
from qiskit_ibm_runtime.options_models.measure_noise_learning_options import (
    MeasureNoiseLearningOptions,
)
from qiskit_ibm_runtime.options_models.twirling_options import TwirlingOptions
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
        noise_model_mapping = [{"r2feB": noise_model}]

        noise_factors = [1, 1.5, 2, 2.5, 3]

        shots = 1024
        quantum_program = prepare_pea(
            [pub], TwirlingOptions(), shots, noise_factors, noise_model_mapping
        )

        self.assertIsInstance(quantum_program, QuantumProgram)
        self.assertEqual(quantum_program.shots, 64)
        self.assertEqual(quantum_program._semantic_role, "estimator_v2")
        self.assertEqual(len(quantum_program.items), 1)

        item = cast("SamplexItem", quantum_program.items[0])
        self.assertIsInstance(item, SamplexItem)
        # Check samplex shape
        auto_num_rand = math.ceil(shots / (max(64, math.ceil(shots / 32))))
        expected_shape = (auto_num_rand, 1, len(noise_factors))
        self.assertEqual(item.shape, expected_shape)

        # Check that samplex_arguments contains pauli_lindblad_maps
        self.assertIn("pauli_lindblad_maps.r2feB", item.samplex_arguments)
        self.assertEqual(
            item.samplex_arguments["pauli_lindblad_maps.r2feB"], noise_model_mapping[0]["r2feB"]
        )

        # Check that samplex_arguments contains noise_scales for the layer
        self.assertIn("noise_scales.r2feB", item.samplex_arguments)
        # noise_scales = noise_factors - 1
        expected_noise_scales = np.array(noise_factors) - 1
        self.assertTrue(
            np.all(item.samplex_arguments["noise_scales.r2feB"] == expected_noise_scales)
        )

        # Check passthrough_data contains pea_noise_factors
        passthrough = cast("dict[str, Any]", quantum_program.passthrough_data)
        self.assertIn("pea_noise_factors", passthrough["post_processor"])
        self.assertEqual(passthrough["post_processor"]["pea_noise_factors"], noise_factors)

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
        noise_model_mapping = [
            {"r2feB": noise_model_1},
            {"rf55B": noise_model_2a, "rd2dB": noise_model_2b},
        ]

        noise_factors = [1, 1.5, 2, 2.5, 3]

        shots = 2048
        quantum_program = prepare_pea(
            [pub1, pub2], TwirlingOptions(), shots, noise_factors, noise_model_mapping
        )

        self.assertEqual(len(quantum_program.items), 2)

        # Check first item
        item1 = cast("SamplexItem", quantum_program.items[0])
        self.assertIn("pauli_lindblad_maps.r2feB", item1.samplex_arguments)
        self.assertEqual(
            item1.samplex_arguments["pauli_lindblad_maps.r2feB"], noise_model_mapping[0]["r2feB"]
        )
        self.assertIn("noise_scales.r2feB", item1.samplex_arguments)
        expected_noise_scales = np.array(noise_factors) - 1
        self.assertTrue(
            np.all(item1.samplex_arguments["noise_scales.r2feB"] == expected_noise_scales)
        )

        # Check second item
        item2 = cast("SamplexItem", quantum_program.items[1])
        self.assertIn("pauli_lindblad_maps.rf55B", item2.samplex_arguments)
        self.assertIn("pauli_lindblad_maps.rd2dB", item2.samplex_arguments)
        self.assertEqual(
            item2.samplex_arguments["pauli_lindblad_maps.rf55B"], noise_model_mapping[1]["rf55B"]
        )
        self.assertEqual(
            item2.samplex_arguments["pauli_lindblad_maps.rd2dB"], noise_model_mapping[1]["rd2dB"]
        )
        self.assertIn("noise_scales.rf55B", item2.samplex_arguments)
        self.assertIn("noise_scales.rd2dB", item2.samplex_arguments)
        self.assertTrue(
            np.all(item2.samplex_arguments["noise_scales.rf55B"] == expected_noise_scales)
        )
        self.assertTrue(
            np.all(item2.samplex_arguments["noise_scales.rd2dB"] == expected_noise_scales)
        )

        # Check passthrough_data contains pec_gammas for both pubs
        passthrough = cast("dict[str, Any]", quantum_program.passthrough_data)
        self.assertIn("pea_noise_factors", passthrough["post_processor"])
        self.assertEqual(passthrough["post_processor"]["pea_noise_factors"], noise_factors)

    def test_prepare_pea_raises_error_without_noise_model_mapping(self):
        """Test that prepare_pea raises error when noise_model_mapping is None."""
        circuit = QuantumCircuit(2)
        circuit.h(0)
        circuit.cx(0, 1)

        observable = SparsePauliOp.from_list([("ZZ", 1)])
        pub = EstimatorPub.coerce((circuit, observable))

        noise_factors = [1, 1.5, 2, 2.5, 3]

        with self.assertRaises(IBMInputValueError) as context:
            prepare_pea([pub], TwirlingOptions(), 1024, noise_factors, None)

        self.assertIn("noise_model_mapping", str(context.exception))

    def test_prepare_pea_raises_error_with_mismatched_noise_model_mapping_length(self):
        """Test that prepare_pea raises error when noise_model_mapping length doesn't match pubs."""
        circuit1 = QuantumCircuit(2)
        circuit1.h(0)
        circuit1.cx(0, 1)

        circuit2 = QuantumCircuit(2)
        circuit2.h(0)
        circuit2.cx(0, 1)

        observable = SparsePauliOp.from_list([("ZZ", 1)])
        pub1 = EstimatorPub.coerce((circuit1, observable))
        pub2 = EstimatorPub.coerce((circuit2, observable))

        # Only provide noise model for one pub, but we have two pubs
        noise_model = PauliLindbladMap.from_sparse_list([("XX", [0, 1], 0.1)], num_qubits=2)
        noise_model_mapping = [{"r2feB": noise_model}]

        noise_factors = [1, 1.5, 2, 2.5, 3]

        with self.assertRaises(IBMInputValueError) as context:
            prepare_pea([pub1, pub2], TwirlingOptions(), 1024, noise_factors, noise_model_mapping)

        self.assertIn("noise_model_mapping", str(context.exception))

    def test_prepare_pea_with_measure_noise_learning(self):
        """Test prepare_pea with measure noise learning (TREX)."""
        circuit = QuantumCircuit(2)
        circuit.h(0)
        circuit.cx(0, 1)

        observable = SparsePauliOp.from_list([("ZZ", 1)])
        pub = EstimatorPub.coerce((circuit, observable))

        noise_model = PauliLindbladMap.from_sparse_list([("XX", [0, 1], 0.1)], num_qubits=2)
        noise_model_mapping = [{"r2feB": noise_model}]

        noise_factors = [1, 1.5, 2, 2.5, 3]

        measure_noise_learning = MeasureNoiseLearningOptions()
        measure_noise_learning.num_randomizations = 16

        quantum_program = prepare_pea(
            [pub],
            TwirlingOptions(),
            1024,
            noise_factors,
            noise_model_mapping,
            measure_noise_learning,
        )

        # Should have 2 items: 1 for pub + 1 TREX calibration
        self.assertEqual(len(quantum_program.items), 2)

        # Check first item has PEA arguments
        item = cast("SamplexItem", quantum_program.items[0])
        self.assertIn("pauli_lindblad_maps.r2feB", item.samplex_arguments)
        self.assertEqual(
            item.samplex_arguments["pauli_lindblad_maps.r2feB"], noise_model_mapping[0]["r2feB"]
        )
        self.assertIn("noise_scales.r2feB", item.samplex_arguments)
        expected_noise_scales = np.array(noise_factors) - 1
        self.assertTrue(
            np.all(item.samplex_arguments["noise_scales.r2feB"] == expected_noise_scales)
        )

        # Check passthrough data
        passthrough = cast("dict[str, Any]", quantum_program.passthrough_data)
        self.assertEqual(passthrough["post_processor"]["measure_mitigation"], "True")
        self.assertIn("pea_noise_factors", passthrough["post_processor"])
        self.assertEqual(passthrough["post_processor"]["pea_noise_factors"], noise_factors)
