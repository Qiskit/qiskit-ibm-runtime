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
from typing import Any, cast

import numpy as np
from ddt import data, ddt, unpack
from qiskit.circuit import Parameter, QuantumCircuit
from qiskit.primitives.containers.estimator_pub import EstimatorPub
from qiskit.quantum_info import PauliLindbladMap, SparsePauliOp
from samplomatic import InjectNoise
from samplomatic.utils import get_annotation

from qiskit_ibm_runtime.exceptions import IBMInputValueError
from qiskit_ibm_runtime.executor_estimator.prepare_pea import prepare_pea
from qiskit_ibm_runtime.executor_estimator.utils import find_unique_layers
from qiskit_ibm_runtime.options_models.measure_noise_learning import MeasureNoiseLearningOptions
from qiskit_ibm_runtime.options_models.twirling import TwirlingOptions
from qiskit_ibm_runtime.options_models.zne import ZneOptions
from qiskit_ibm_runtime.quantum_program import QuantumProgram
from qiskit_ibm_runtime.quantum_program.quantum_program import SamplexItem

from ...ibm_test_case import IBMEstimatorPrepareTestCase
from .utils import PARAM_BASIS_3Q_SCENARIOS, SAMPLEX_CIRCUIT_SCENARIOS, TEMPLATE_CIRCUIT_SCENARIO


@ddt
class TestPreparePea(IBMEstimatorPrepareTestCase):
    """Tests for the ``prepare_pea`` function."""

    @data([True, True], [False, False])
    @unpack
    def test_param_basis_expansion_3q(self, enable_measure, enable_measure_noise_learning):
        """Test parameter-basis expansion with three-qubit observables."""
        observables = PARAM_BASIS_3Q_SCENARIOS.observables
        num_qubits = observables.num_qubits

        circuit = QuantumCircuit(num_qubits)
        circuit.rz(Parameter("alpha"), 0)

        twirling_options = TwirlingOptions()
        twirling_options.enable_gates = True
        twirling_options.enable_measure = enable_measure

        measure_noise_learning = (
            MeasureNoiseLearningOptions() if enable_measure_noise_learning else None
        )

        zne_options = ZneOptions()
        zne_options.amplifier = "pea"
        zne_options.noise_factors = [1, 2, 3, 4]

        for scenario in PARAM_BASIS_3Q_SCENARIOS.scenarios:
            parameter_shape = scenario.parameter_shape
            observables_shape = scenario.observables_shape
            expected_pairs = scenario.expected_pairs

            with self.subTest(value=(parameter_shape, observables_shape, expected_pairs)):
                pub_like = (
                    circuit,
                    observables.reshape(observables_shape),
                    np.random.random(parameter_shape + (circuit.num_parameters,)),
                )
                pubs = [EstimatorPub.coerce(pub_like)]

                program = prepare_pea(
                    pubs=pubs,
                    twirling_options=twirling_options,
                    shots=10,
                    zne_options=zne_options,
                    noise_model_mapping={},
                    measure_noise_learning=measure_noise_learning,
                )

                post_processor_data = program.passthrough_data["post_processor"]
                param_basis_pairs = post_processor_data["param_basis_pairs"][0]

                # Check that the param-basis pairs are the correct ones
                self.assertListEqual(param_basis_pairs, expected_pairs, msg=param_basis_pairs)

                # Check that the quantum program has one element per param-basis pair
                self.assertEqual(
                    program.items[0].shape,
                    (len(zne_options.noise_factors), 1, len(expected_pairs)),
                )

    @data([True, False], [False, False], [True, True])
    @unpack
    def test_samplex_arguments_structure(self, enable_measure, enable_measure_noise_learning):
        """Test that samplex arguments have the expected structure for each circuit type."""
        twirling_options = TwirlingOptions()
        twirling_options.enable_gates = True
        twirling_options.enable_measure = enable_measure

        measure_noise_learning = (
            MeasureNoiseLearningOptions() if enable_measure_noise_learning else None
        )

        zne_options = ZneOptions()
        zne_options.amplifier = "pea"
        zne_options.noise_factors = [1, 2, 3]

        # Build a noise model mapping covering the layers of all scenario pubs.
        # Must use the same twirling_options as the prepare call, since different
        # options produce different layer refs.
        pubs = [scenario.pub for scenario in SAMPLEX_CIRCUIT_SCENARIOS]
        layers = find_unique_layers(pubs, twirling_options, inject_noise=True)
        noise_model_mapping = {
            annot.ref: PauliLindbladMap.from_sparse_list(
                [("Z" * len(layer.qubits), list(range(len(layer.qubits))), 0.1)],
                num_qubits=len(layer.qubits),
            )
            for layer in layers
            if (annot := get_annotation(layer.operation, InjectNoise))
        }

        for scenario in SAMPLEX_CIRCUIT_SCENARIOS:
            with self.subTest(circuit=scenario.label):
                program = prepare_pea(
                    pubs=[scenario.pub],
                    twirling_options=twirling_options,
                    shots=10,
                    zne_options=zne_options,
                    noise_model_mapping=noise_model_mapping,
                    measure_noise_learning=measure_noise_learning,
                )
                # PEA always requires enable_gates=True
                self.assertSamplexArgumentsAreCorrect(program.items[0], scenario, inject_noise=True)

    @data(True, False)
    def test_template_circuit(self, enable_measure):
        """Test that the template circuit has the expected clbits and parameter count.

        Uses a single circuit combining 2Q gates, a parametric gate, and a mid-circuit
        measurement — covering all structural features of template compilation.
        PEA always runs with enable_gates=True.
        """
        twirling_options = TwirlingOptions()
        twirling_options.enable_gates = True
        twirling_options.enable_measure = enable_measure

        zne_options = ZneOptions()
        zne_options.amplifier = "pea"
        zne_options.noise_factors = [1, 2, 3]

        scenario = TEMPLATE_CIRCUIT_SCENARIO
        pubs = [scenario.pub]
        layers = find_unique_layers(pubs, twirling_options, inject_noise=True)
        noise_model_mapping = {
            annot.ref: PauliLindbladMap.from_sparse_list(
                [("Z" * len(layer.qubits), list(range(len(layer.qubits))), 0.1)],
                num_qubits=len(layer.qubits),
            )
            for layer in layers
            if (annot := get_annotation(layer.operation, InjectNoise))
        }

        program = prepare_pea(
            pubs=pubs,
            twirling_options=twirling_options,
            shots=10,
            zne_options=zne_options,
            noise_model_mapping=noise_model_mapping,
        )
        self.assertTemplateCircuitIsCorrect(program.items[0], scenario, enable_gates=True)

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
        # The expected shape is (num_noise_factors, num_randomizations, bases * num_param_sets)
        expected_shape = (len(noise_factors), auto_num_rand, 1)
        self.assertEqual(item.shape, expected_shape)

        # Check that samplex_arguments contains pauli_lindblad_maps
        self.assertIn(f"pauli_lindblad_maps.{noise_layer_ref}", item.samplex_arguments)
        self.assertEqual(
            item.samplex_arguments[f"pauli_lindblad_maps.{noise_layer_ref}"],
            noise_model_mapping[noise_layer_ref],
        )

        # Check that samplex_arguments contains noise_scales for the layer
        self.assertIn(f"noise_scales.{noise_layer_ref}", item.samplex_arguments)
        # noise_scales = noise_factors - 1, shape is (num_noise_factors, 1, 1)
        expected_noise_scales = np.array([[[factor - 1]] for factor in noise_factors])
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
        self.assertTrue(passthrough["post_processor"]["mitigation"] == "pea")

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
        # noise_scales shape is (num_noise_factors, 1, 1)
        expected_noise_scales = np.array([[[factor - 1]] for factor in noise_factors])
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

        with self.assertRaisesRegex(IBMInputValueError, "Noise model is missing"):
            prepare_pea([pub], twirling_options, 1024, zne_options, {})

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

        with self.assertRaisesRegex(IBMInputValueError, "Noise model is missing"):
            prepare_pea([pub1, pub2], twirling_options, 1024, zne_options, noise_model_mapping)

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
        # noise_scales shape is (num_noise_factors, 1, 1)
        expected_noise_scales = np.array([[[factor - 1]] for factor in noise_factors])
        self.assertTrue(
            np.all(
                item.samplex_arguments[f"noise_scales.{noise_layer_ref}"] == expected_noise_scales
            )
        )

        # Check passthrough data
        passthrough = cast("dict[str, Any]", quantum_program.passthrough_data)
        self.assertTrue(passthrough["post_processor"]["measure_mitigation"])
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
        # The expected shape is (num_noise_factors, num_randomizations, bases * num_param_sets)
        # num_randomizations is calculated automatically based on shots
        auto_num_rand = math.ceil(shots / (max(64, math.ceil(shots / 32))))
        num_param_sets = parameter_values.shape[0]  # 3
        num_observables = 1  # Single observable
        num_noise_factors = len(noise_factors)  # 5

        expected_shape = (num_noise_factors, auto_num_rand, num_param_sets * num_observables)
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

        # Verify noise_scales are correct (noise_factors - 1), shape is (num_noise_factors, 1, 1)
        expected_noise_scales = np.array([[[factor - 1]] for factor in noise_factors])
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

    def test_prepare_pea_raises_error_with_less_than_2_noise_factors(self):
        """Test that prepare_pea raises when noise_factors has less than 2 points."""
        zne_options = ZneOptions()
        zne_options.amplifier = "pea"
        with self.assertRaisesRegex(ValueError, "Must have at least two noise factors"):
            zne_options.noise_factors = [1.5]

    def test_prepare_pea_raises_error_with_too_few_noise_factors_for_extrapolator(self):
        """Test that prepare_pea rejects noise_factors under-specified for the extrapolator."""
        circuit = QuantumCircuit(2)
        circuit.h(0)
        observable = SparsePauliOp.from_list([("ZZ", 1)])
        pub = EstimatorPub.coerce((circuit, observable))

        twirling_options = TwirlingOptions()
        twirling_options.enable_gates = True

        zne_options = ZneOptions()
        zne_options.amplifier = "pea"
        zne_options.extrapolator = "double_exponential"
        zne_options.noise_factors = [1.0, 3.0]

        with self.assertRaisesRegex(
            IBMInputValueError, "double_exponential requires at least 4 noise_factors"
        ):
            prepare_pea(
                [pub], twirling_options, shots=100, zne_options=zne_options, noise_model_mapping={}
            )
