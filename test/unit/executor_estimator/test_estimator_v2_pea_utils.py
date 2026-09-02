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
from samplomatic.quantum_program import SamplexItem
from samplomatic.utils import get_annotation

from qiskit_ibm_runtime.exceptions import IBMInputValueError
from qiskit_ibm_runtime.executor_estimator.prepare_pea import prepare_pea
from qiskit_ibm_runtime.executor_estimator.utils import find_unique_layers
from qiskit_ibm_runtime.options_models.measure_noise_learning import MeasureNoiseLearningOptions
from qiskit_ibm_runtime.options_models.twirling import TwirlingOptions
from qiskit_ibm_runtime.options_models.zne import ZneOptions
from qiskit_ibm_runtime.quantum_program import QuantumProgram

from ...ibm_test_case import IBMEstimatorPrepareTestCase
from .utils import (
    PARAM_BASIS_3Q_SCENARIOS,
    SAMPLEX_CIRCUIT_SCENARIOS,
    TEMPLATE_CIRCUIT_SCENARIO,
    TWIRLING_SHAPE_SCENARIOS,
)


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
                    noise_model={},
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
        noise_model = {
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
                    noise_model=noise_model,
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
        noise_model = {
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
            noise_model=noise_model,
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

        noise_model = {noise_layer_ref: noise_model}

        noise_factors = [1, 1.5, 2, 2.5, 3]
        zne_options = ZneOptions()
        zne_options.amplifier = "pea"
        zne_options.noise_factors = noise_factors

        twirling_options = TwirlingOptions()
        twirling_options.enable_gates = True
        twirling_options.enable_measure = True

        shots = 1024
        quantum_program = prepare_pea([pub], twirling_options, shots, zne_options, noise_model)

        self.assertIsInstance(quantum_program, QuantumProgram)
        self.assertEqual(quantum_program.shots, 64)
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
            noise_model[noise_layer_ref],
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

    def test_prepare_pea_raises_error_with_empty_noise_model(self):
        """Test that prepare_pea raises error when noise_model is empty."""
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
        """Test that prepare_pea raises error when noise_model is missing a noise model."""
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

        noise_model = {noise_layer_ref_pub1: noise_model}

        noise_factors = [1, 1.5, 2, 2.5, 3]
        zne_options = ZneOptions()
        zne_options.amplifier = "pea"
        zne_options.noise_factors = noise_factors

        twirling_options = TwirlingOptions()
        twirling_options.enable_gates = True
        twirling_options.enable_measure = True

        with self.assertRaisesRegex(IBMInputValueError, "Noise model is missing"):
            prepare_pea([pub1, pub2], twirling_options, 1024, zne_options, noise_model)

    @data(32, "auto")
    def test_prepare_pea_with_measure_noise_learning(self, num_randomizations):
        """Test that measure_noise_learning adds a correctly built TREX calibration item.

        Uses two pubs of different widths (2q and 3q).  Verifies item count, circuit gate
        structure, shape, and passthrough data via :meth:`assertTrexItemIsCorrect`.
        """
        circuit1 = QuantumCircuit(2)
        circuit1.h(0)
        circuit1.cx(0, 1)
        circuit2 = QuantumCircuit(3)
        circuit2.h(0)
        circuit2.cx(0, 1)
        circuit2.cx(1, 2)

        pub1 = EstimatorPub.coerce((circuit1, SparsePauliOp.from_list([("ZZ", 1)])))
        pub2 = EstimatorPub.coerce((circuit2, SparsePauliOp.from_list([("ZZZ", 1)])))
        pubs = [pub1, pub2]

        twirling_options = TwirlingOptions()
        twirling_options.enable_gates = True
        twirling_options.enable_measure = True
        twirling_options.num_randomizations = 64

        noise_model = self._build_trivial_noise_model(pubs, twirling_options)

        zne_options = ZneOptions()
        zne_options.amplifier = "pea"
        zne_options.noise_factors = [1.0, 2.0]

        measure_noise_learning = MeasureNoiseLearningOptions()
        measure_noise_learning.num_randomizations = num_randomizations

        program = prepare_pea(
            pubs, twirling_options, 1024, zne_options, noise_model, measure_noise_learning
        )

        # 2 pubs + 1 TREX calibration item.
        self.assertEqual(len(program.items), 3)
        # For "auto", TREX follows the twirling randomizations of the estimation items.
        expected_trex_randomizations = (
            twirling_options.num_randomizations
            if num_randomizations == "auto"
            else num_randomizations
        )
        self.assertTrexItemIsCorrect(
            program, pubs, expected_num_randomizations=expected_trex_randomizations
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
            prepare_pea([pub], twirling_options, shots=100, zne_options=zne_options, noise_model={})

    def _build_trivial_noise_model(self, pubs, twirling_options):
        """Build a trivial (zero-rate) noise model mapping for the given PUBs."""
        layers = find_unique_layers(pubs, twirling_options, inject_noise=True)
        return {
            annot.ref: PauliLindbladMap.from_sparse_list([], num_qubits=len(layer.qubits))
            for layer in layers
            if (annot := get_annotation(layer.operation, InjectNoise))
        }

    def test_shapes_twirling_configs(self):
        """Verify the number of randomization and program.shots.

        PEA shape is (num_noise_factors, num_randomizations, num_basis).
        """
        noise_factors = [1.0, 3.0]
        zne_options = ZneOptions()
        zne_options.amplifier = "pea"
        zne_options.noise_factors = noise_factors

        qc = QuantumCircuit(2)
        qc.h(0)
        qc.cx(0, 1)
        pub = EstimatorPub.coerce((qc, SparsePauliOp.from_list([("ZZ", 1)])))

        for scenario in TWIRLING_SHAPE_SCENARIOS:
            if not scenario.twirling_options.enable_gates:
                continue  # PEA requires enable_gates=True
            with self.subTest(twirling=scenario.label):
                noise_model = self._build_trivial_noise_model([pub], scenario.twirling_options)
                program = prepare_pea(
                    pubs=[pub],
                    twirling_options=scenario.twirling_options,
                    shots=scenario.shots,
                    zne_options=zne_options,
                    noise_model=noise_model,
                )
                item = program.items[0]
                self.assertEqual(
                    item.shape[0],
                    len(noise_factors),
                    msg=f"[{scenario.label}] expected N={len(noise_factors)}, got {item.shape[0]}",
                )
                self.assertEqual(
                    item.shape[1],
                    scenario.expected_num_randomizations,
                    msg=f"[{scenario.label}] expected R={scenario.expected_num_randomizations}, "
                    f"got {item.shape[1]}",
                )
                self.assertEqual(
                    program.shots,
                    scenario.expected_shots_per_randomization,
                    msg=f"[{scenario.label}] expected program.shots="
                    f"{scenario.expected_shots_per_randomization}, got {program.shots}",
                )
