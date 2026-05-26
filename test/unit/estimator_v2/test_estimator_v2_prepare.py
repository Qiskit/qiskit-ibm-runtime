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

"""Unit tests for EstimatorV2 prepare function."""

import unittest
from typing import Any, cast
from unittest.mock import MagicMock, patch
import numpy as np
from ddt import ddt, data, unpack

from qiskit import QuantumCircuit
from qiskit.circuit import Parameter
from qiskit.primitives.containers.estimator_pub import EstimatorPub, ObservablesArray
from qiskit.quantum_info import SparsePauliOp
from qiskit.circuit import ClassicalRegister

from qiskit_ibm_runtime.executor_estimator.prepare import compute_samplex_arguments, prepare
from qiskit_ibm_runtime.options_models.twirling_options import TwirlingOptions
from qiskit_ibm_runtime.options_models.measure_noise_learning_options import (
    MeasureNoiseLearningOptions,
)
from qiskit_ibm_runtime.quantum_program import QuantumProgram
from qiskit_ibm_runtime.quantum_program.quantum_program import SamplexItem
from qiskit_ibm_runtime.exceptions import IBMInputValueError


@ddt
class TestPrepareFunction(unittest.TestCase):
    """Tests for the prepare function."""

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
        program = prepare([pub], TwirlingOptions(), 10, False, MeasureNoiseLearningOptions())

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
        program = prepare([pub], TwirlingOptions(), 10, False, MeasureNoiseLearningOptions())

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

        shots = 1024
        quantum_program = prepare(
            [pub1, pub2], TwirlingOptions(), shots, False, MeasureNoiseLearningOptions()
        )

        self.assertIsInstance(quantum_program, QuantumProgram)
        self.assertEqual(quantum_program.shots, shots)
        self.assertEqual(quantum_program.meas_level, "classified")
        self.assertEqual(quantum_program._semantic_role, "estimator_v2")
        self.assertEqual(len(quantum_program.items), 2)

        item1 = cast(SamplexItem, quantum_program.items[0])
        item2 = cast(SamplexItem, quantum_program.items[1])
        self.assertIsInstance(item1, SamplexItem)
        self.assertIsInstance(item2, SamplexItem)

        self.assertEqual(item1.shape, (1, 3))
        self.assertEqual(item2.shape, (1, 2))

        self.assertNotIn("parameter_values", item1.samplex_arguments)
        np.testing.assert_allclose(item2.samplex_arguments["parameter_values"], parameter_values2)

        passthrough = cast(dict[str, Any], quantum_program.passthrough_data)
        self.assertEqual(passthrough["post_processor"]["version"], "v0.1")
        self.assertEqual(len(passthrough["post_processor"]["observables"]), 2)
        self.assertEqual(len(passthrough["post_processor"]["observables"][0]), 3)
        self.assertEqual(len(passthrough["post_processor"]["observables"][1]), 2)
        self.assertEqual(len(passthrough["post_processor"]["param_basis_pairs"]), 2)
        self.assertEqual(len(passthrough["post_processor"]["param_shapes"]), 2)
        self.assertEqual(passthrough["post_processor"]["param_shapes"][0], ())
        self.assertEqual(passthrough["post_processor"]["param_shapes"][1], (2,))

    @patch("qiskit_ibm_runtime.executor_estimator.prepare.generate_boxing_pass_manager")
    def test_prepare_passes_twirling_values_to_boxing_pass_manager(self, mock_generate_boxing_pm):
        """Test that boxing pass manager receives the expected twirling values."""
        mock_boxing_pm = MagicMock()
        mock_boxing_pm.run.side_effect = lambda circuit: circuit
        mock_generate_boxing_pm.return_value = mock_boxing_pm

        twirling_options = TwirlingOptions()
        twirling_options.enable_gates = True
        twirling_options.enable_measure = False
        twirling_options.strategy = "all"

        circuit = QuantumCircuit(2)
        circuit.h(0)
        circuit.cx(0, 1)
        observable = SparsePauliOp.from_list([("ZZ", 1)])
        pub = EstimatorPub.coerce((circuit, observable))

        mock_samplex = MagicMock()
        basis_changes_spec = MagicMock()
        basis_changes_spec.name = "basis_changes"
        mock_samplex.inputs.return_value.get_specs.return_value = [basis_changes_spec]
        mock_samplex.inputs.return_value.make_broadcastable.return_value = MagicMock()

        with patch(
            "qiskit_ibm_runtime.executor_estimator.prepare.build",
            return_value=(circuit, mock_samplex),
        ):
            prepare([pub], twirling_options, 1024, False, MeasureNoiseLearningOptions())

        mock_generate_boxing_pm.assert_called_once_with(
            enable_gates=True,
            enable_measures=True,
            twirling_strategy="all",
            measure_annotations="change_basis",
        )

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

        quantum_program = prepare([pub], twirling_options, 2000, False, MeasureNoiseLearningOptions())

        self.assertIsInstance(quantum_program.items[0], SamplexItem)
        self.assertEqual(quantum_program.shots, 256)
        self.assertEqual(quantum_program.items[0].shape, (4, 1))
        self.assertEqual(quantum_program.items[0].circuit.num_parameters, 3 * circuit.num_qubits)

    def test_prepare_with_mid_circuit_measurements_raises(self):
        """Test that prepare raises error for circuits with mid-circuit measurements."""
        # Create a circuit with mid-circuit measurements
        circuit = QuantumCircuit(3, 3)
        circuit.h(0)
        circuit.cx(0, 1)
        # Add mid-circuit measurement
        circuit.measure(0, 0)
        # Continue with more gates after measurement
        circuit.h(0)
        circuit.cx(0, 2)

        observable = SparsePauliOp.from_list([("ZZZ", 1)])
        pub = EstimatorPub.coerce((circuit, observable))

        shots = 1024

        # Should raise an error - mid-circuit measurements are not supported
        with self.assertRaises(IBMInputValueError) as context:
            prepare([pub], TwirlingOptions(), shots, False, MeasureNoiseLearningOptions())

        self.assertIn("mid-circuit measurements", str(context.exception))

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

        # Should raise an error - the classical register name is reserved
        with self.assertRaises(IBMInputValueError) as context:
            prepare([pub], TwirlingOptions(), 1024, False, MeasureNoiseLearningOptions())

        self.assertIn("_meas", str(context.exception))
        self.assertIn("reserved", str(context.exception))

    def test_prepare_with_measure_mitigation_adds_trex_item(self):
        """Test that measure_mitigation=True adds a TREX calibration item to QuantumProgram."""
        circuit = QuantumCircuit(2)
        circuit.h(0)
        circuit.cx(0, 1)

        observable = SparsePauliOp.from_list([("ZZ", 1)])
        pub = EstimatorPub.coerce((circuit, observable))

        shots = 1024
        measure_noise_learning = MeasureNoiseLearningOptions()
        measure_noise_learning.num_randomizations = 16

        # Test without measure mitigation
        quantum_program_no_mitigation = prepare(
            [pub], TwirlingOptions(), shots, False, measure_noise_learning
        )
        self.assertEqual(len(quantum_program_no_mitigation.items), 1)

        # Test with measure mitigation
        quantum_program_with_mitigation = prepare(
            [pub], TwirlingOptions(), shots, True, measure_noise_learning
        )

        # Should have one additional item (the TREX calibration circuit)
        self.assertEqual(len(quantum_program_with_mitigation.items), 2)

        # Verify the additional item is a SamplexItem
        trex_item = quantum_program_with_mitigation.items[-1]
        self.assertIsInstance(trex_item, SamplexItem)

        # Verify passthrough data contains measure_mitigation flag
        passthrough = cast(dict[str, Any], quantum_program_with_mitigation.passthrough_data)
        self.assertEqual(passthrough["post_processor"]["measure_mitigation"], "True")

    def test_prepare_with_measure_mitigation_trex_circuit_has_only_measurements(self):
        """Test that TREX calibration circuit is based on measurement-only operations.
        
        The TREX circuit template will have parameterized gates for measurement twirling,
        but it should be derived from a circuit that only performs measurements (no state preparation).
        """
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

        shots = 1024
        measure_noise_learning = MeasureNoiseLearningOptions()
        measure_noise_learning.num_randomizations = 32

        quantum_program = prepare(
            [pub1, pub2], TwirlingOptions(), shots, True, measure_noise_learning
        )

        # Get the TREX calibration item (last item)
        trex_item = quantum_program.items[-1]
        self.assertIsInstance(trex_item, SamplexItem)

        # Get the circuit from the TREX item
        trex_circuit = trex_item.circuit

        # Verify the circuit has measurements
        self.assertGreater(trex_circuit.num_clbits, 0, "TREX circuit should have classical bits")
        
        # Verify the circuit has measurement operations
        has_measurements = any(
            instruction.operation.name == "measure" for instruction in trex_circuit.data
        )
        self.assertTrue(has_measurements, "TREX circuit should contain measurement operations")

        # Verify it has the expected number of qubits (union of all pub qubits)
        # circuit1 has 2 qubits, circuit2 has 3 qubits, so union should be 3
        self.assertEqual(trex_circuit.num_qubits, 3)

        # Verify the shape matches the number of randomizations
        self.assertEqual(trex_item.shape, (32,))
        
        # Verify the circuit has parameters (for measurement twirling)
        self.assertGreater(
            trex_circuit.num_parameters,
            0,
            "TREX circuit should have parameters for measurement twirling",
        )

    @data(
        [16, (16,)],
        [32, (32,)],
        [64, (64,)],
        [128, (128,)],
    )
    @unpack
    def test_prepare_with_measure_mitigation_num_randomizations(
        self, num_randomizations, expected_shape
    ):
        """Test that measure_noise_learning.num_randomizations affects TREX item shape."""
        circuit = QuantumCircuit(2)
        circuit.h(0)
        circuit.cx(0, 1)

        observable = SparsePauliOp.from_list([("ZZ", 1)])
        pub = EstimatorPub.coerce((circuit, observable))

        shots = 1024
        measure_noise_learning = MeasureNoiseLearningOptions()
        measure_noise_learning.num_randomizations = num_randomizations

        quantum_program = prepare(
            [pub], TwirlingOptions(), shots, True, measure_noise_learning
        )

        # Get the TREX calibration item (last item)
        trex_item = quantum_program.items[-1]
        self.assertIsInstance(trex_item, SamplexItem)

        # Verify the shape matches the number of randomizations
        self.assertEqual(
            trex_item.shape,
            expected_shape,
            f"Expected TREX item shape {expected_shape} for num_randomizations={num_randomizations}",
        )

    def test_prepare_with_measure_mitigation_default_num_randomizations(self):
        """Test that TREX item uses default num_randomizations=32 when not specified."""
        circuit = QuantumCircuit(2)
        circuit.h(0)
        circuit.cx(0, 1)

        observable = SparsePauliOp.from_list([("ZZ", 1)])
        pub = EstimatorPub.coerce((circuit, observable))

        shots = 1024
        # Create MeasureNoiseLearningOptions without setting num_randomizations
        measure_noise_learning = MeasureNoiseLearningOptions()

        quantum_program = prepare(
            [pub], TwirlingOptions(), shots, True, measure_noise_learning
        )

        # Get the TREX calibration item (last item)
        trex_item = quantum_program.items[-1]
        self.assertIsInstance(trex_item, SamplexItem)

        # Verify the shape uses default value of 32
        self.assertEqual(
            trex_item.shape,
            (32,),
            "Expected TREX item shape (32,) when num_randomizations is not set",
        )

    def test_prepare_with_measure_mitigation_multiple_pubs_num_randomizations(self):
        """Test that num_randomizations affects TREX item with multiple pubs."""
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

        shots = 1024
        measure_noise_learning = MeasureNoiseLearningOptions()
        measure_noise_learning.num_randomizations = 48

        quantum_program = prepare(
            [pub1, pub2], TwirlingOptions(), shots, True, measure_noise_learning
        )

        # Should have 3 items: 2 for pubs + 1 TREX calibration
        self.assertEqual(len(quantum_program.items), 3)

        # Get the TREX calibration item (last item)
        trex_item = quantum_program.items[-1]
        self.assertIsInstance(trex_item, SamplexItem)

        # Verify the shape matches the specified num_randomizations
        self.assertEqual(
            trex_item.shape,
            (48,),
            "Expected TREX item shape (48,) for num_randomizations=48",
        )


@ddt
class TestComputeSamplexArguments(unittest.TestCase):
    """Tests for ``compute_samplex_arguments``."""

    @data([(2, 2), (2, 2)], [(2, 2, 1), (2, 2)], [(2, 2), (2, 2, 1)], [(), (2, 2, 1)])
    @unpack
    def test_shapes_returned_arrays(self, param_shape, obs_shape):
        """Test the shapes of the returned params and change basis arrays."""
        circuit = QuantumCircuit(3)
        if param_shape:
            for idx in range(7):
                circuit.rz(Parameter(f"th_{idx}"), 0)
        circuit.cx(0, 1)
        circuit.measure_all()

        pub_like = (
            circuit,
            ObservablesArray(["ZZZ", "XXX", "YYY", "IYI"]).reshape(obs_shape),
            np.random.random(param_shape + (circuit.num_parameters,)),
        )
        pub = EstimatorPub.coerce(pub_like)

        flat_parameter_values, change_basis, param_basis_pairs = compute_samplex_arguments(pub)
        num_basis = len(param_basis_pairs)

        self.assertEqual(flat_parameter_values.ndim, 2)
        self.assertEqual(flat_parameter_values.shape, (num_basis, pub.circuit.num_parameters))

        self.assertEqual(change_basis.ndim, 2)
        self.assertEqual(change_basis.shape, (num_basis, pub.circuit.num_qubits))

    @data(
        [
            (2, 2),
            (2, 2),
            [
                ((0, 0), "ZZZ"),
                ((0, 1), "XXX"),
                ((1, 0), "YYY"),
                ((1, 1), "IYI"),
            ],
        ],
        [
            (2, 2),
            (2, 2, 1),
            [
                ((0, 0), "ZZZ"),
                ((0, 0), "YYY"),
                ((0, 1), "ZZZ"),
                ((0, 1), "YYY"),
                ((1, 0), "XXX"),
                ((1, 0), "IYI"),
                ((1, 1), "XXX"),
                ((1, 1), "IYI"),
            ],
        ],
        [
            (2, 2, 1),
            (2, 2),
            [
                ((0, 0, 0), "ZZZ"),
                ((0, 0, 0), "XXX"),
                ((0, 1, 0), "YYY"),
                ((1, 0, 0), "ZZZ"),
                ((1, 0, 0), "XXX"),
                ((1, 1, 0), "YYY"),
            ],
        ],
        [(), (2, 2), [((), "ZZZ"), ((), "XXX"), ((), "YYY")]],
    )
    @unpack
    def test_param_basis_pairs(self, param_shape, obs_shape, expected_pairs):
        """Test the shapes of the returned ``param_basis_pairs`` list."""
        circuit = QuantumCircuit(3)
        if param_shape:
            for idx in range(7):
                circuit.rz(Parameter(f"th_{idx}"), 0)
        circuit.cx(0, 1)
        circuit.measure_all()

        pub_like = (
            circuit,
            ObservablesArray(["ZZZ", "XXX", "YYY", "IYI"]).reshape(obs_shape),
            np.random.random(param_shape + (circuit.num_parameters,)),
        )
        pub = EstimatorPub.coerce(pub_like)

        _, _, param_basis_pairs = compute_samplex_arguments(pub)
        self.assertListEqual(param_basis_pairs, expected_pairs, msg=param_basis_pairs)
