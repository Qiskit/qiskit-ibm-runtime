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

from typing import Any, cast

import numpy as np
from ddt import data, ddt, unpack
from qiskit.circuit import Parameter, QuantumCircuit
from qiskit.primitives.containers.estimator_pub import EstimatorPub
from qiskit.quantum_info import SparsePauliOp

from qiskit_ibm_runtime.exceptions import IBMInputValueError
from qiskit_ibm_runtime.executor_estimator.zne.prepare_zne import prepare_zne
from qiskit_ibm_runtime.options_models.measure_noise_learning import MeasureNoiseLearningOptions
from qiskit_ibm_runtime.options_models.twirling import TwirlingOptions
from qiskit_ibm_runtime.options_models.zne import ZneOptions
from qiskit_ibm_runtime.quantum_program import QuantumProgram
from qiskit_ibm_runtime.quantum_program.quantum_program import SamplexItem

from ...ibm_test_case import IBMEstimatorPrepareTestCase
from ...utils import combine
from .utils import PARAM_BASIS_3Q_SCENARIOS, SAMPLEX_CIRCUIT_SCENARIOS, TEMPLATE_CIRCUIT_SCENARIO


@ddt
class TestPrepareZne(IBMEstimatorPrepareTestCase):
    """Tests for the ``prepare_zne`` function."""

    @data([True, True, True], [False, True, True], [False, False, False])
    @unpack
    def test_param_basis_expansion_3q(
        self, enable_gates, enable_measure, enable_measure_noise_learning
    ):
        """Test parameter-basis expansion with three-qubit observables."""
        observables = PARAM_BASIS_3Q_SCENARIOS.observables
        num_qubits = observables.num_qubits

        circuit = QuantumCircuit(num_qubits)
        circuit.rz(Parameter("alpha"), 0)

        twirling_options = TwirlingOptions()
        twirling_options.enable_gates = enable_gates
        twirling_options.enable_measure = enable_measure

        measure_noise_learning = (
            MeasureNoiseLearningOptions() if enable_measure_noise_learning else None
        )

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

                program = prepare_zne(
                    pubs=pubs,
                    twirling_options=twirling_options,
                    shots=10,
                    zne_options=ZneOptions(),
                    measure_noise_learning=measure_noise_learning,
                )

                post_processor_data = program.passthrough_data["post_processor"]
                param_basis_pairs = post_processor_data["param_basis_pairs"][0]

                # Check that the param-basis pairs are the correct ones
                self.assertListEqual(param_basis_pairs, expected_pairs, msg=param_basis_pairs)

                # Check that the quantum program has one element per param-basis pair
                self.assertEqual(program.items[0].shape, (1, len(expected_pairs)))

    @data(
        [True, True, True],
        [False, True, True],
        [False, False, False],
        [True, False, False],
        [False, True, False],
        [True, True, False],
    )
    @unpack
    def test_samplex_arguments_structure(
        self, enable_gates, enable_measure, enable_measure_noise_learning
    ):
        """Test that samplex arguments have the expected structure for each circuit type."""
        twirling_options = TwirlingOptions()
        twirling_options.enable_gates = enable_gates
        twirling_options.enable_measure = enable_measure

        measure_noise_learning = (
            MeasureNoiseLearningOptions() if enable_measure_noise_learning else None
        )

        zne_options = ZneOptions()
        zne_options.amplifier = "gate_folding"
        zne_options.noise_factors = [1, 3, 5]

        for scenario in SAMPLEX_CIRCUIT_SCENARIOS:
            with self.subTest(circuit=scenario.label):
                program = prepare_zne(
                    pubs=[scenario.pub],
                    twirling_options=twirling_options,
                    shots=10,
                    zne_options=zne_options,
                    measure_noise_learning=measure_noise_learning,
                )
                # One item per noise factor; skip any trailing TREX item.
                for item in program.items[: len(zne_options.noise_factors)]:
                    self.assertSamplexArgumentsAreCorrect(item, scenario, inject_noise=False)

    @combine(enable_gates=[True, False], enable_measure=[True, False])
    def test_template_circuit(self, enable_gates, enable_measure):
        """Test that the template circuit has the expected clbits and parameter count.

        Uses a single circuit combining 2Q gates, a parametric gate, and a mid-circuit
        measurement. Verifies that gate folding at each noise factor scales only the
        gate-twirling parameters, leaving measurement-box parameters fixed.
        """
        twirling_options = TwirlingOptions()
        twirling_options.enable_gates = enable_gates
        twirling_options.enable_measure = enable_measure

        zne_options = ZneOptions()
        zne_options.amplifier = "gate_folding"
        zne_options.noise_factors = [1, 3, 5]

        scenario = TEMPLATE_CIRCUIT_SCENARIO
        program = prepare_zne(
            pubs=[scenario.pub],
            twirling_options=twirling_options,
            shots=10,
            zne_options=zne_options,
        )
        # One item per noise factor; verify that the template scales correctly.
        for noise_factor, item in zip(
            zne_options.noise_factors, program.items[: len(zne_options.noise_factors)]
        ):
            with self.subTest(noise_factor=noise_factor):
                self.assertTemplateCircuitIsCorrect(
                    item, scenario, enable_gates=enable_gates, noise_factor=noise_factor
                )

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
        extrapolated_noise_factors = passthrough["post_processor"]["extrapolated_noise_factors"]
        expected_extrapolated_noise_factors = [0.0, 1.0, 2.0, 3.0]
        self.assertTrue(
            np.array_equal(extrapolated_noise_factors, expected_extrapolated_noise_factors)
        )
        extrapolator = passthrough["post_processor"]["extrapolator"]
        expected_extrapolator = ("exponential", "linear")
        self.assertEqual(extrapolator, expected_extrapolator)

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

    def test_prepare_zne_with_single_noise_factor(self):
        """Test prepare_zne with a single noise factor."""
        noise_factors = [1.5]
        zne_options = ZneOptions()
        zne_options.amplifier = "gate_folding_back"
        with self.assertRaisesRegex(ValueError, "Must have at least two noise factors"):
            zne_options.noise_factors = noise_factors

    def test_prepare_zne_with_empty_noise_factors_list(self):
        """Test prepare_zne behavior with empty noise_factors list."""
        noise_factors = []
        zne_options = ZneOptions()
        zne_options.amplifier = "gate_folding"
        with self.assertRaisesRegex(ValueError, "Must have at least two noise factors"):
            zne_options.noise_factors = noise_factors

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
        self.assertTrue(passthrough["post_processor"]["measure_mitigation"])

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

    def test_prepare_zne_raises_error_with_less_than_2_noise_factors(self):
        """Test that prepare_zne raises when noise_factors has less than 2 points."""
        zne_options = ZneOptions()
        zne_options.amplifier = "gate_folding"
        with self.assertRaisesRegex(ValueError, "Must have at least two noise factors"):
            zne_options.noise_factors = [1.5]

    def test_prepare_zne_raises_error_with_too_few_noise_factors_for_extrapolator(self):
        """Test that prepare_zne rejects noise_factors under-specified for the extrapolator."""
        circuit = QuantumCircuit(2)
        circuit.h(0)
        observable = SparsePauliOp.from_list([("ZZ", 1)])
        pub = EstimatorPub.coerce((circuit, observable))

        twirling_options = TwirlingOptions()

        zne_options = ZneOptions()
        zne_options.amplifier = "gate_folding"
        zne_options.extrapolator = "double_exponential"
        zne_options.noise_factors = [1.0, 3.0]

        with self.assertRaisesRegex(
            IBMInputValueError, "double_exponential requires at least 4 noise_factors"
        ):
            prepare_zne([pub], twirling_options, 100, zne_options)
