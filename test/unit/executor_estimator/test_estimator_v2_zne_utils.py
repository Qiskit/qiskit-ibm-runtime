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

"""Unit tests for EstimatorV2 ZNE helper functions."""

import unittest
from typing import Any, cast

import numpy as np
from ddt import data, ddt
from qiskit import QuantumCircuit
from qiskit.circuit import Parameter
from qiskit.primitives.containers.estimator_pub import EstimatorPub
from qiskit.quantum_info import SparsePauliOp

from qiskit_ibm_runtime.executor_estimator.zne.prepare_zne import prepare_zne
from qiskit_ibm_runtime.options_models.measure_noise_learning_options import (
    MeasureNoiseLearningOptions,
)
from qiskit_ibm_runtime.options_models.twirling_options import TwirlingOptions
from qiskit_ibm_runtime.options_models.zne_options import ZneOptions
from qiskit_ibm_runtime.quantum_program import QuantumProgram
from qiskit_ibm_runtime.quantum_program.quantum_program import SamplexItem


@ddt
class TestPrepareZneFunction(unittest.TestCase):
    """Tests for the prepare_zne function."""

    def test_prepare_zne_basic(self):
        """Test prepare_zne with basic ZNE options."""
        circuit = QuantumCircuit(2)
        circuit.h(0)
        circuit.cx(0, 1)

        observable = SparsePauliOp.from_list([("ZZ", 1)])
        pub = EstimatorPub.coerce((circuit, observable))

        noise_factors = [1.0, 2.0, 3.0]
        zne_options = ZneOptions()
        zne_options.amplifier = "gate_folding"
        zne_options.noise_factors = noise_factors
        shots = 1024
        quantum_program = prepare_zne([pub], TwirlingOptions(), shots, zne_options)

        self.assertIsInstance(quantum_program, QuantumProgram)
        self.assertEqual(quantum_program.shots, shots)
        self.assertEqual(quantum_program._semantic_role, "estimator_v2")
        # Should have len(noise_factors) items for the single pub
        self.assertEqual(len(quantum_program.items), len(noise_factors))

        for item in quantum_program.items:
            self.assertIsInstance(item, SamplexItem)

        # Check passthrough_data contains zne_noise_factors
        passthrough = cast("dict[str, Any]", quantum_program.passthrough_data)
        self.assertIn("zne_noise_factors", passthrough["post_processor"])
        self.assertTrue(
            np.array_equal(
                np.array(passthrough["post_processor"]["zne_noise_factors"]),
                np.array(noise_factors),
            )
        )
        self.assertIn("item_id", passthrough["post_processor"])
        expected_map = [(0, 1.0), (0, 2.0), (0, 3.0)]
        self.assertEqual(passthrough["post_processor"]["item_id"], expected_map)

    def test_prepare_zne_multiple_pubs(self):
        """Test prepare_zne with multiple pubs."""
        circuit1 = QuantumCircuit(2)
        circuit1.h(0)
        circuit1.cx(0, 1)

        circuit2 = QuantumCircuit(3)
        circuit2.h(0)
        circuit2.cx(0, 1)
        circuit2.cx(1, 2)

        observable1 = SparsePauliOp.from_list([("ZZ", 1), ("XX", 1), ("YY", 1)])
        observable2 = SparsePauliOp.from_list([("ZZZ", 1)])

        pub1 = EstimatorPub.coerce((circuit1, observable1))
        pub2 = EstimatorPub.coerce((circuit2, observable2))

        noise_factors = [1.0, 2.0]
        zne_options = ZneOptions()
        zne_options.amplifier = "gate_folding_front"
        zne_options.noise_factors = noise_factors
        shots = 2048
        quantum_program = prepare_zne([pub1, pub2], TwirlingOptions(), shots, zne_options)

        # Should have len(pubs) * len(noise_factors) items
        expected_items = 2 * len(noise_factors)
        self.assertEqual(len(quantum_program.items), expected_items)
        # Check items shape
        auto_num_rand = 1  # no twirling - single randomization
        pub1_items = len(noise_factors)
        for i, item in enumerate(quantum_program.items):
            if i < pub1_items:
                num_observables = len(observable1)  # 3
            else:
                num_observables = len(observable2)
            expected_shape = (auto_num_rand, num_observables)
            self.assertEqual(item.shape, expected_shape)

        # Check passthrough_data
        passthrough = cast("dict[str, Any]", quantum_program.passthrough_data)
        self.assertEqual(len(passthrough["post_processor"]["observables"]), 2)
        self.assertEqual(len(passthrough["post_processor"]["observables"][0]), 3)
        self.assertEqual(len(passthrough["post_processor"]["observables"][1]), 1)
        self.assertTrue(
            np.array_equal(
                np.array(passthrough["post_processor"]["zne_noise_factors"]),
                np.array(noise_factors),
            )
        )
        self.assertIn("item_id", passthrough["post_processor"])
        expected_map = [(0, 1.0), (0, 2.0), (1, 1.0), (1, 2.0)]
        self.assertEqual(passthrough["post_processor"]["item_id"], expected_map)

    def test_prepare_zne_with_single_noise_factor(self):
        """Test prepare_zne with a single noise factor."""
        circuit = QuantumCircuit(2)
        circuit.h(0)
        circuit.cx(0, 1)

        observable = SparsePauliOp.from_list([("ZZ", 1)])
        pub = EstimatorPub.coerce((circuit, observable))

        noise_factors = [1.5]
        zne_options = ZneOptions()
        zne_options.amplifier = "gate_folding_back"
        zne_options.noise_factors = noise_factors
        shots = 1024
        quantum_program = prepare_zne([pub], TwirlingOptions(), shots, zne_options)

        # Should have 1 item for single pub and single noise factor
        self.assertEqual(len(quantum_program.items), 1)

        item = cast("SamplexItem", quantum_program.items[0])
        self.assertIsInstance(item, SamplexItem)

    def test_prepare_zne_with_empty_noise_factors_list(self):
        """Test prepare_zne behavior with empty noise_factors list."""
        circuit = QuantumCircuit(2)
        circuit.h(0)
        circuit.cx(0, 1)

        observable = SparsePauliOp.from_list([("ZZ", 1)])
        pub = EstimatorPub.coerce((circuit, observable))

        noise_factors = []
        zne_options = ZneOptions()
        zne_options.amplifier = "gate_folding"
        zne_options.noise_factors = noise_factors
        shots = 1024
        quantum_program = prepare_zne([pub], TwirlingOptions(), shots, zne_options)

        # Should have 0 items for empty noise_factors
        self.assertEqual(len(quantum_program.items), 0)

    @data("gate_folding", "gate_folding_front", "gate_folding_back")
    def test_prepare_zne_with_different_folding_methods(self, folding_method):
        """Test prepare_zne with different folding methods."""
        circuit = QuantumCircuit(2)
        circuit.h(0)
        circuit.cx(0, 1)

        observable = SparsePauliOp.from_list([("ZZ", 1)])
        pub = EstimatorPub.coerce((circuit, observable))

        noise_factors = [1.0, 2.0]
        zne_options = ZneOptions()
        zne_options.amplifier = folding_method
        zne_options.noise_factors = noise_factors
        shots = 1024
        quantum_program = prepare_zne([pub], TwirlingOptions(), shots, zne_options)

        self.assertIsInstance(quantum_program, QuantumProgram)
        self.assertEqual(len(quantum_program.items), len(noise_factors))

    def test_prepare_zne_with_parameterized_circuit(self):
        """Test prepare_zne with parameterized circuit."""
        circuit = QuantumCircuit(2)
        theta = Parameter("theta")
        phi = Parameter("phi")
        circuit.rx(theta, 0)
        circuit.ry(phi, 1)
        circuit.cx(0, 1)

        observable = SparsePauliOp.from_list([("ZZ", 1)])
        parameter_values = np.array([[0.1, 0.2], [0.3, 0.4]])
        pub = EstimatorPub.coerce((circuit, observable, parameter_values))

        noise_factors = [1.0, 2.0]
        zne_options = ZneOptions()
        zne_options.amplifier = "gate_folding"
        zne_options.noise_factors = noise_factors
        shots = 1024
        quantum_program = prepare_zne([pub], TwirlingOptions(), shots, zne_options)

        # Should have len(noise_factors) items
        self.assertEqual(len(quantum_program.items), len(noise_factors))

        # Check that parameter values are in samplex_arguments and check item shape
        auto_num_rand = 1  # no twirling - single randomization
        num_param_sets = parameter_values.shape[0]  # 2
        num_observables = 1  # Single observable
        expected_shape = (auto_num_rand, num_param_sets * num_observables)
        for item in quantum_program.items:
            item_cast = cast("SamplexItem", item)
            self.assertIn("parameter_values", item_cast.samplex_arguments)
            self.assertEqual(item.shape, expected_shape)

    def test_prepare_zne_with_twirling(self):
        """Test that items have correct shapes based on twirling and observables."""
        circuit = QuantumCircuit(2)
        circuit.h(0)
        circuit.cx(0, 1)

        observables = SparsePauliOp.from_list([("ZZ", 1), ("XX", 1)])
        pub = EstimatorPub.coerce((circuit, observables))

        twirling_options = TwirlingOptions()
        twirling_options.enable_gates = True
        twirling_options.num_randomizations = 8

        noise_factors = [1.0, 2.0]
        zne_options = ZneOptions()
        zne_options.amplifier = "gate_folding"
        zne_options.noise_factors = noise_factors
        shots = 1024
        quantum_program = prepare_zne([pub], twirling_options, shots, zne_options)

        # Should have len(noise_factors) items
        self.assertEqual(len(quantum_program.items), len(noise_factors))
        # Each item should have shape (num_randomizations, num_basis_changes)
        # With 2 observables (ZZ, XX), we need 2 basis changes (Z and X basis)
        for item in quantum_program.items:
            item_cast = cast("SamplexItem", item)
            self.assertEqual(item_cast.shape, (8, 2))

    def test_prepare_zne_single_pub_with_measure_noise_learning(self):
        """Test prepare_zne with measure noise learning (TREX)."""
        circuit = QuantumCircuit(2)
        circuit.h(0)
        circuit.cx(0, 1)

        observable = SparsePauliOp.from_list([("ZZ", 1)])
        pub = EstimatorPub.coerce((circuit, observable))

        noise_factors = [1.0, 2.0]
        zne_options = ZneOptions()
        zne_options.amplifier = "gate_folding"
        zne_options.noise_factors = noise_factors
        measure_noise_learning = MeasureNoiseLearningOptions()
        measure_noise_learning.num_randomizations = 16

        twirling_options = TwirlingOptions()
        twirling_options.enable_gates = True
        twirling_options.enable_measure = True

        quantum_program = prepare_zne(
            [pub],
            twirling_options,
            1024,
            zne_options,
            measure_noise_learning=measure_noise_learning,
        )

        # Should have len(noise_factors) items + 1 TREX calibration
        self.assertEqual(len(quantum_program.items), len(noise_factors) + 1)

        # Check passthrough data
        passthrough = cast("dict[str, Any]", quantum_program.passthrough_data)
        self.assertEqual(passthrough["post_processor"]["measure_mitigation"], "True")

    def test_prepare_zne_multiple_pubs_with_measure_noise_learning(self):
        """Test prepare_zne with multiple pubs and TREX."""
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

        noise_factors = [1.0, 2.0]
        zne_options = ZneOptions()
        zne_options.amplifier = "gate_folding"
        zne_options.noise_factors = noise_factors
        measure_noise_learning = MeasureNoiseLearningOptions()
        measure_noise_learning.num_randomizations = 32

        twirling_options = TwirlingOptions()
        twirling_options.enable_gates = True
        twirling_options.enable_measure = True

        quantum_program = prepare_zne(
            [pub1, pub2],
            twirling_options,
            1024,
            zne_options,
            measure_noise_learning=measure_noise_learning,
        )

        # Should have 2 pubs * 2 noise_factors + 1 TREX calibration = 5 items
        self.assertEqual(len(quantum_program.items), 5)

        # Last item should be TREX calibration
        trex_item = quantum_program.items[-1]
        self.assertIsInstance(trex_item, SamplexItem)
        self.assertEqual(trex_item.shape, (32,))
