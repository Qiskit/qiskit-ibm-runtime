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

from qiskit import QuantumCircuit
from qiskit.circuit import Parameter
from qiskit.primitives.containers.estimator_pub import EstimatorPub, ObservablesArray
from qiskit.quantum_info import SparsePauliOp
from qiskit.circuit import ClassicalRegister

from qiskit_ibm_runtime.executor_estimator.prepare import prepare
from qiskit_ibm_runtime.options_models.estimator_options import EstimatorOptions
from qiskit_ibm_runtime.quantum_program import QuantumProgram
from qiskit_ibm_runtime.quantum_program.quantum_program import SamplexItem
from qiskit_ibm_runtime.exceptions import IBMInputValueError


class TestPrepareFunction(unittest.TestCase):
    """Tests for the prepare function."""

    def setUp(self):
        """Set up test fixtures."""
        self.options = EstimatorOptions()

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
        quantum_program = prepare([pub1, pub2], self.options.twirling, shots)

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
        self.assertEqual(item2.shape, (1, 2, 2))

        self.assertNotIn("parameter_values", item1.samplex_arguments)
        np.testing.assert_allclose(
            item2.samplex_arguments["parameter_values"],
            parameter_values2.reshape((2, 1, 2)),
        )

        passthrough = cast(dict[str, Any], quantum_program.passthrough_data)
        self.assertEqual(passthrough["post_processor"]["version"], "v0.1")
        self.assertEqual(len(passthrough["observables"]), 2)
        self.assertEqual(len(passthrough["observables"][0]), 3)
        self.assertEqual(len(passthrough["observables"][1]), 2)
        self.assertEqual(len(passthrough["measure_bases"]), 2)
        self.assertEqual(len(passthrough["measure_bases"][0]), 3)
        self.assertEqual(len(passthrough["measure_bases"][1]), 2)

    @patch("qiskit_ibm_runtime.executor_estimator.prepare.generate_boxing_pass_manager")
    def test_prepare_passes_twirling_values_to_boxing_pass_manager(self, mock_generate_boxing_pm):
        """Test that boxing pass manager receives the expected twirling values."""
        mock_boxing_pm = MagicMock()
        mock_boxing_pm.run.side_effect = lambda circuit: circuit
        mock_generate_boxing_pm.return_value = mock_boxing_pm

        options = EstimatorOptions()
        options.twirling.enable_gates = True
        options.twirling.enable_measure = False
        options.twirling.strategy = "all"

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
            prepare([pub], options.twirling, 1024)

        mock_generate_boxing_pm.assert_called_once_with(
            enable_gates=True,
            enable_measures=True,
            twirling_strategy="all",
            measure_annotations="change_basis",
        )

    def test_prepare_with_twirling_enabled(self):
        """Test prepare with gate and measurement twirling enabled."""
        options = EstimatorOptions()
        options.twirling.enable_gates = True
        options.twirling.enable_measure = True
        options.twirling.num_randomizations = 4
        options.twirling.shots_per_randomization = 256

        circuit = QuantumCircuit(2)
        circuit.rx(0.1, 0)
        circuit.ry(0.2, 1)

        observables = ObservablesArray.coerce([{"ZI": 1}, {"IZ": 1}])
        pub = EstimatorPub.coerce((circuit, observables))

        quantum_program = prepare([pub], options.twirling, 2000)

        item = cast(SamplexItem, quantum_program.items[0])
        self.assertEqual(quantum_program.shots, 256)
        self.assertEqual(item.shape, (4, 1))
        self.assertEqual(item.circuit.num_parameters, 3 * circuit.num_qubits)

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
            prepare([pub], self.options.twirling, shots)

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
            prepare([pub], self.options.twirling, 1024)

        self.assertIn("_meas", str(context.exception))
        self.assertIn("reserved", str(context.exception))
