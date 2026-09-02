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

"""Unit tests for EstimatorV2 prepare vanilla function."""

from typing import Any, cast

import numpy as np
from ddt import data, ddt, unpack
from qiskit import QuantumCircuit
from qiskit.circuit import ClassicalRegister, Parameter
from qiskit.primitives.containers.estimator_pub import EstimatorPub, ObservablesArray
from qiskit.quantum_info import SparsePauliOp
from samplomatic.quantum_program import SamplexItem

from qiskit_ibm_runtime.exceptions import IBMInputValueError
from qiskit_ibm_runtime.executor_estimator.prepare_vanilla import prepare_vanilla
from qiskit_ibm_runtime.options_models.measure_noise_learning import MeasureNoiseLearningOptions
from qiskit_ibm_runtime.options_models.twirling import TwirlingOptions
from qiskit_ibm_runtime.quantum_program import QuantumProgram

from ...ibm_test_case import IBMEstimatorPrepareTestCase
from ...utils import combine
from .utils import (
    PARAM_BASIS_3Q_SCENARIOS,
    SAMPLEX_CIRCUIT_SCENARIOS,
    TEMPLATE_CIRCUIT_SCENARIO,
    TWIRLING_SHAPE_SCENARIOS,
)


@ddt
class TestPrepareVanilla(IBMEstimatorPrepareTestCase):
    """Tests for the ``prepare_vanilla`` function."""

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

                program = prepare_vanilla(
                    pubs=pubs,
                    twirling_options=twirling_options,
                    shots=10,
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

        for scenario in SAMPLEX_CIRCUIT_SCENARIOS:
            with self.subTest(circuit=scenario.label):
                program = prepare_vanilla(
                    pubs=[scenario.pub],
                    twirling_options=twirling_options,
                    shots=10,
                    measure_noise_learning=measure_noise_learning,
                )
                self.assertSamplexArgumentsAreCorrect(
                    program.items[0], scenario, inject_noise=False
                )

    @combine(enable_gates=[True, False], enable_measure=[True, False])
    def test_template_circuit(self, enable_gates, enable_measure):
        """Test that the template circuit has the expected clbits and parameter count.

        Uses a single circuit combining 2Q gates, a parametric gate, and a mid-circuit
        measurement — covering all structural features of template compilation.
        """
        twirling_options = TwirlingOptions()
        twirling_options.enable_gates = enable_gates
        twirling_options.enable_measure = enable_measure

        scenario = TEMPLATE_CIRCUIT_SCENARIO
        program = prepare_vanilla(
            pubs=[scenario.pub],
            twirling_options=twirling_options,
            shots=10,
        )
        self.assertTemplateCircuitIsCorrect(program.items[0], scenario, enable_gates=enable_gates)

    @data(
        [(2, 2), (2, 2), (1, 4)],
        [(2, 2, 1), (2, 2), (1, 6)],
        [(2, 2), (2, 2, 1), (1, 8)],
        [(), (2, 2, 1), (1, 3)],
    )
    @unpack
    def test_shapes(self, param_shape, obs_shape, item_shape):
        """Test preparing with different shapes of observables and params."""
        circuit = QuantumCircuit(3)
        if param_shape:
            for idx in range(7):
                circuit.rz(Parameter(f"th_{idx}"), 0)
        circuit.cx(0, 1)
        circuit.measure_all()

        params = np.random.random(param_shape + (circuit.num_parameters,))

        obs = ObservablesArray(["ZZZ", "XXX", "YYY", "IYI"]).reshape(obs_shape)

        pub = EstimatorPub.coerce((circuit, obs, params))

        twirling_options = TwirlingOptions()
        twirling_options.enable_gates = True
        twirling_options.enable_measure = True
        program = prepare_vanilla([pub], twirling_options, 10, MeasureNoiseLearningOptions())

        self.assertEqual(program.items[0].shape, item_shape)

    @data(
        [(2, 2), (2, 2), (1, 5)],
        [(2, 2, 1), (2, 2), (1, 8)],
        [(2, 2), (2, 2, 1), (1, 10)],
        [(), (2, 2, 1), (1, 4)],
    )
    @unpack
    def test_shapes_with_nested_observables(self, param_shape, obs_shape, item_shape):
        """Test preparing with different shapes of (nested) observables and params."""
        circuit = QuantumCircuit(3)
        if param_shape:
            for idx in range(7):
                circuit.rz(Parameter(f"th_{idx}"), 0)
        circuit.cx(0, 1)
        circuit.measure_all()

        params = np.random.random(param_shape + (circuit.num_parameters,))

        obs = ObservablesArray(["ZZZ", "XXX", {"YYY": 1, "XZX": 1}, "I0I"]).reshape(obs_shape)

        pub = EstimatorPub.coerce((circuit, obs, params))

        twirling_options = TwirlingOptions()
        twirling_options.enable_gates = True
        twirling_options.enable_measure = True
        program = prepare_vanilla([pub], twirling_options, 10, MeasureNoiseLearningOptions())

        self.assertEqual(program.items[0].shape, item_shape)

    def test_prepare_general_case(self):
        """Test prepare with multiple pubs, observables, and parameter values."""
        circuit1 = QuantumCircuit(2)
        circuit1.h(0)
        circuit1.cx(0, 1)

        circuit2 = QuantumCircuit(2)
        theta = Parameter("theta")
        phi = Parameter("phi")
        circuit2.rx(theta, 0)
        circuit2.ry(phi, 1)
        circuit2.cx(0, 1)

        observables1 = ObservablesArray.coerce([{"ZZ": 1}, {"XX": 1}, {"YY": 1}])
        observables2 = ObservablesArray.coerce([{"ZZ": 1}, {"XX": 1}])
        parameter_values2 = np.array([[0.1, 0.2], [0.3, 0.4]])

        pub1 = EstimatorPub.coerce((circuit1, observables1))
        pub2 = EstimatorPub.coerce((circuit2, observables2, parameter_values2))

        twirling_options = TwirlingOptions()
        twirling_options.enable_gates = False
        twirling_options.enable_measure = False

        shots = 1024
        quantum_program = prepare_vanilla([pub1, pub2], twirling_options, shots)

        self.assertIsInstance(quantum_program, QuantumProgram)
        self.assertEqual(quantum_program.shots, shots)
        self.assertEqual(quantum_program.meas_level, "classified")
        self.assertEqual(len(quantum_program.items), 2)

        item1 = cast("SamplexItem", quantum_program.items[0])
        item2 = cast("SamplexItem", quantum_program.items[1])
        self.assertIsInstance(item1, SamplexItem)
        self.assertIsInstance(item2, SamplexItem)

        self.assertEqual(item1.shape, (1, 3))
        self.assertEqual(item2.shape, (1, 2))

        self.assertNotIn("parameter_values", item1.samplex_arguments)
        np.testing.assert_allclose(item2.samplex_arguments["parameter_values"], parameter_values2)

        passthrough = cast("dict[str, Any]", quantum_program.passthrough_data)
        self.assertEqual(passthrough["post_processor"]["version"], "v0.1")
        self.assertEqual(len(passthrough["post_processor"]["observables"]), 2)
        self.assertEqual(len(passthrough["post_processor"]["observables"][0]), 3)
        self.assertEqual(len(passthrough["post_processor"]["observables"][1]), 2)
        self.assertEqual(len(passthrough["post_processor"]["param_basis_pairs"]), 2)
        self.assertEqual(len(passthrough["post_processor"]["param_shapes"]), 2)
        self.assertEqual(passthrough["post_processor"]["param_shapes"][0], ())
        self.assertEqual(passthrough["post_processor"]["param_shapes"][1], (2,))

    def test_prepare_with_twirling_enabled(self):
        """Test prepare with gate and measurement twirling enabled."""
        twirling_options = TwirlingOptions()
        twirling_options.enable_gates = True
        twirling_options.enable_measure = True
        twirling_options.num_randomizations = 4
        twirling_options.shots_per_randomization = 256

        circuit = QuantumCircuit(2)
        circuit.rx(0.1, 0)
        circuit.ry(0.2, 1)

        observables = ObservablesArray.coerce([{"ZI": 1}, {"IZ": 1}])
        pub = EstimatorPub.coerce((circuit, observables))

        quantum_program = prepare_vanilla([pub], twirling_options, 2000)

        self.assertIsInstance(quantum_program.items[0], SamplexItem)
        self.assertEqual(quantum_program.shots, 256)
        self.assertEqual(quantum_program.items[0].shape, (4, 1))
        self.assertEqual(quantum_program.items[0].circuit.num_parameters, 3 * circuit.num_qubits)

    @combine(enable_gates=[True, False], enable_measure=[True, False])
    def test_prepare_with_mid_circuit_measurements(self, enable_gates, enable_measure):
        """Test the prepare function for circuits with mid-circuit measurements."""
        if enable_measure or not (enable_gates or enable_measure):
            self.skipTest(
                "Mid-circuit measurements are not yet fully supported by samplomatic, see"
                "Samplomatic issue #361."
            )

        circuit = QuantumCircuit(3, 3)
        circuit.h(0)
        circuit.cx(0, 1)
        # Add mid-circuit measurement
        circuit.measure(0, 0)
        # Continue with more gates after measurement
        circuit.h(0)
        circuit.cx(0, 2)

        observable = SparsePauliOp.from_list([("ZZZ", 1), ("XXX", 1), ("YYY", 1), ("IZI", 1)])
        pub = EstimatorPub.coerce((circuit, observable))

        twirling_options = TwirlingOptions()
        twirling_options.enable_gates = enable_gates
        twirling_options.enable_measure = enable_measure
        twirling_options.num_randomizations = 7
        twirling_options.strategy = "all"
        program = prepare_vanilla(pubs=[pub], twirling_options=twirling_options, shots=1024)

        self.assertEqual(len(program.items), 1)
        self.assertIsInstance(program.items[0], SamplexItem)
        self.assertEqual(len(program.items[0].samplex.inputs().specs), 2)

        # 7 randomizations, 3 basis
        self.assertEqual(program.items[0].shape, (7 if enable_gates or enable_measure else 1, 3))

        # We expect two `basis_changes` specs, but can't be sure how they'll be ordered.
        # So we verify that we have exactly one of each expected specs.
        specs = program.items[0].samplex.inputs().specs
        for spec in specs:
            self.assertTrue(spec.name.startswith("basis_changes"))
            self.assertEqual(spec.shape, (3,))

        samplex_args = program.items[0].samplex_arguments
        mid_circuit_names = [
            name for name in samplex_args if np.array_equal(samplex_args[name], np.zeros(3))
        ]
        final_meas_names = [
            name
            for name in samplex_args
            if np.array_equal(samplex_args[name], np.array([[2, 2, 2], [3, 3, 3], [1, 1, 1]]))
        ]
        self.assertEqual(
            len(mid_circuit_names),
            1,
            msg=f"Expected 1 mid-circuit spec with zeros, got: {samplex_args}",
        )
        self.assertEqual(
            len(final_meas_names),
            1,
            msg=f"Expected 1 final-meas spec with change_basis, got: {samplex_args}",
        )

    def test_prepare_with_reserved_classical_register_name_raises(self):
        """Test that prepare raises error when circuit uses reserved classical register name."""
        # Create a circuit with the reserved classical register name
        circuit = QuantumCircuit(2)
        circuit.h(0)
        circuit.cx(0, 1)

        # Add a classical register with the reserved name
        reserved_creg = ClassicalRegister(2, "_meas")
        circuit.add_register(reserved_creg)

        observable = SparsePauliOp.from_list([("ZZ", 1)])
        pub = EstimatorPub.coerce((circuit, observable))

        twirling_options = TwirlingOptions()
        twirling_options.enable_gates = True
        twirling_options.enable_measure = True

        # Should raise an error - the classical register name is reserved
        with self.assertRaises(IBMInputValueError) as context:
            prepare_vanilla([pub], twirling_options, 1024)

        self.assertIn("_meas", str(context.exception))
        self.assertIn("reserved", str(context.exception))

    @data(32, "auto")
    def test_prepare_with_measure_noise_learning(self, num_randomizations):
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

        measure_noise_learning = MeasureNoiseLearningOptions()
        measure_noise_learning.num_randomizations = num_randomizations

        program = prepare_vanilla(
            pubs, twirling_options, shots=1024, measure_noise_learning=measure_noise_learning
        )

        # Two estimation items (one per pub) + one TREX calibration item.
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

    def test_shapes_twirling_configs(self):
        """Verify the number of randomization and program.shots."""
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.cx(0, 1)
        pub = EstimatorPub.coerce((qc, SparsePauliOp.from_list([("ZZ", 1)])))

        for scenario in TWIRLING_SHAPE_SCENARIOS:
            with self.subTest(twirling=scenario.label):
                program = prepare_vanilla(
                    pubs=[pub],
                    twirling_options=scenario.twirling_options,
                    shots=scenario.shots,
                )
                item = program.items[0]
                self.assertEqual(
                    item.shape[0],
                    scenario.expected_num_randomizations,
                    msg=f"[{scenario.label}] expected R={scenario.expected_num_randomizations}, "
                    f"got {item.shape[0]}",
                )
                self.assertEqual(
                    program.shots,
                    scenario.expected_shots_per_randomization,
                    msg=f"[{scenario.label}] expected program.shots="
                    f"{scenario.expected_shots_per_randomization}, got {program.shots}",
                )
