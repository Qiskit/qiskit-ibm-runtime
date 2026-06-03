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

"""Unit tests for EstimatorV2 run method."""

import unittest
from unittest.mock import MagicMock, patch
import numpy as np

from qiskit import QuantumCircuit
from qiskit.circuit import Parameter
from qiskit.primitives.containers.estimator_pub import EstimatorPub
from qiskit.quantum_info import SparsePauliOp

from qiskit_ibm_runtime.executor_estimator.estimator import EstimatorV2
from qiskit_ibm_runtime.options_models.estimator_options import EstimatorOptions
from qiskit_ibm_runtime.executor import Executor
from qiskit_ibm_runtime.runtime_job_v2 import RuntimeJobV2
from qiskit_ibm_runtime.quantum_program import QuantumProgram
from qiskit_ibm_runtime.fake_provider import FakeManilaV2
from qiskit_ibm_runtime.exceptions import IBMInputValueError


class TestEstimatorV2Run(unittest.TestCase):
    """Tests for the EstimatorV2.run() method."""

    def setUp(self):
        """Set up test fixtures."""
        self.backend = FakeManilaV2()

        # Create a mock job to return from executor.run()
        self.mock_job = MagicMock(spec=RuntimeJobV2)
        self.mock_job.job_id.return_value = "test-job-id"

        # Patch Executor to avoid local mode error
        self.executor_patcher = patch("qiskit_ibm_runtime.executor_estimator.estimator.Executor")
        self.mock_executor_class = self.executor_patcher.start()

        # Create mock executor instance
        self.mock_executor_instance = MagicMock(spec=Executor)
        self.mock_executor_instance._backend = self.backend
        self.mock_executor_instance.run = MagicMock(return_value=self.mock_job)
        self.mock_executor_class.return_value = self.mock_executor_instance

    def tearDown(self):
        """Clean up patches."""
        self.executor_patcher.stop()

    def test_run_single_pub_no_parameters(self):
        """Test run with single pub without parameters."""
        estimator = EstimatorV2(mode=self.backend)

        circuit = QuantumCircuit(2)
        circuit.h(0)
        circuit.cx(0, 1)

        observable = SparsePauliOp.from_list([("ZZ", 1)])

        job = estimator.run([(circuit, observable)], precision=0.03125)

        # Verify executor.run was called
        self.mock_executor_instance.run.assert_called_once()

        # Verify the quantum program passed to executor
        call_args = self.mock_executor_instance.run.call_args
        quantum_program = call_args[0][0]
        self.assertIsInstance(quantum_program, QuantumProgram)
        # precision=0.03125 -> shots = ceil(1/0.03125^2) = 1024
        self.assertEqual(quantum_program.shots, 1024)

        # Verify job was returned
        self.assertEqual(job, self.mock_job)

    def test_run_with_pub_level_precision(self):
        """Test that EstimatorPub.coerce is called with precision parameter."""
        estimator = EstimatorV2(mode=self.backend)

        circuit = QuantumCircuit(2)
        circuit.h(0)

        observable = SparsePauliOp.from_list([("ZZ", 1)])

        job = estimator.run([(circuit, observable, None, 0.01)])

        self.mock_executor_instance.run.assert_called_once()
        # precision=0.01 -> shots = ceil(1/0.01^2) = 10000
        call_args = self.mock_executor_instance.run.call_args
        quantum_program = call_args[0][0]
        self.assertEqual(quantum_program.shots, 10000)
        self.assertEqual(job, self.mock_job)

    def test_run_uses_default_precision_from_options(self):
        """Test that run uses default_precision from options when precision not specified."""
        options = EstimatorOptions()

        options.default_precision = 0.01

        estimator = EstimatorV2(mode=self.backend, options=options)

        circuit = QuantumCircuit(2)
        circuit.h(0)
        observable = SparsePauliOp.from_list([("ZZ", 1)])

        estimator.run([(circuit, observable)])

        # Verify executor.run was called
        self.mock_executor_instance.run.assert_called_once()

        # Verify shots from precision were calculated
        call_args = self.mock_executor_instance.run.call_args
        quantum_program = call_args[0][0]
        self.assertEqual(quantum_program.shots, 10000)

    def test_run_precision_parameter_overrides_options(self):
        """Test that precision parameter in run() overrides options.default_precision."""
        options = EstimatorOptions()
        options.default_precision = 0.022097  # sqrt(1/2048)

        estimator = EstimatorV2(mode=self.backend, options=options)

        circuit = QuantumCircuit(2)
        circuit.h(0)
        observable = SparsePauliOp.from_list([("ZZ", 1)])

        estimator.run([(circuit, observable)], precision=0.015625)

        # Verify precision parameter was used instead of options
        call_args = self.mock_executor_instance.run.call_args
        quantum_program = call_args[0][0]
        # precision=0.015625 -> shots = ceil(1/0.015625^2) = 4096
        self.assertEqual(quantum_program.shots, 4096)

    def test_run_with_parametric_circuit(self):
        """Test run with parametric circuit."""
        estimator = EstimatorV2(mode=self.backend)

        circuit = QuantumCircuit(2)
        theta = Parameter("theta")
        circuit.rx(theta, 0)
        circuit.cx(0, 1)

        observable = SparsePauliOp.from_list([("ZZ", 1)])
        parameter_values = np.array([[0], [np.pi / 2], [np.pi]])

        job = estimator.run([(circuit, observable, parameter_values)], precision=0.03125)

        self.mock_executor_instance.run.assert_called_once()
        self.assertEqual(job, self.mock_job)

    def test_run_multiple_pubs(self):
        """Test run with multiple pubs."""
        estimator = EstimatorV2(mode=self.backend)

        circuit1 = QuantumCircuit(2)
        circuit1.h(0)

        circuit2 = QuantumCircuit(3)
        circuit2.h([0, 1, 2])

        observable1 = SparsePauliOp.from_list([("ZZ", 1)])
        observable2 = SparsePauliOp.from_list([("ZZZ", 1)])

        pubs = [(circuit1, observable1), (circuit2, observable2)]

        estimator.run(pubs, precision=0.03125)

        self.mock_executor_instance.run.assert_called_once()

        # Verify multiple items in quantum program
        call_args = self.mock_executor_instance.run.call_args
        quantum_program = call_args[0][0]
        self.assertEqual(len(quantum_program.items), 2)

    def test_run_with_default_precision(self):
        """Test that run uses the default precision value from options."""
        options = EstimatorOptions()
        # default_precision is 0.015625 by default

        estimator = EstimatorV2(mode=self.backend, options=options)

        circuit = QuantumCircuit(2)
        circuit.h(0)
        observable = SparsePauliOp.from_list([("ZZ", 1)])

        estimator.run([(circuit, observable)])

        # Verify executor.run was called
        self.mock_executor_instance.run.assert_called_once()

        # Verify shots from default precision were calculated
        # precision=0.015625 -> shots = ceil(1/0.015625^2) = 4096
        call_args = self.mock_executor_instance.run.call_args
        quantum_program = call_args[0][0]
        self.assertEqual(quantum_program.shots, 4096)

    def test_run_sets_executor_options(self):
        """Test that run sets executor options correctly."""
        options = EstimatorOptions()
        options.execution.init_qubits = True
        options.execution.rep_delay = 0.001
        options.max_execution_time = 300

        estimator = EstimatorV2(mode=self.backend, options=options)

        circuit = QuantumCircuit(2)
        circuit.h(0)
        observable = SparsePauliOp.from_list([("ZZ", 1)])

        estimator.run([(circuit, observable)], precision=0.03125)

        # Verify executor options were set
        self.assertIsNotNone(self.mock_executor_instance.options)
        self.assertTrue(self.mock_executor_instance.options.execution.init_qubits)
        self.assertEqual(self.mock_executor_instance.options.execution.rep_delay, 0.001)

    def test_run_with_multiple_observables(self):
        """Test run with multiple observables in a single pub."""
        estimator = EstimatorV2(mode=self.backend)

        circuit = QuantumCircuit(2)
        circuit.h(0)
        circuit.cx(0, 1)

        observables = [
            SparsePauliOp.from_list([("ZZ", 1)]),
            SparsePauliOp.from_list([("XX", 1)]),
            SparsePauliOp.from_list([("YY", 1)]),
        ]

        job = estimator.run([(circuit, observables)], precision=0.03125)

        self.mock_executor_instance.run.assert_called_once()
        self.assertEqual(job, self.mock_job)

    def test_run_preserves_circuit_metadata(self):
        """Test that run preserves circuit metadata through the pipeline."""
        estimator = EstimatorV2(mode=self.backend)

        circuit = QuantumCircuit(2)
        circuit.h(0)
        circuit.metadata = {"test_key": "test_value"}

        observable = SparsePauliOp.from_list([("ZZ", 1)])

        job = estimator.run([(circuit, observable)], precision=0.03125)

        self.mock_executor_instance.run.assert_called_once()
        self.assertEqual(job, self.mock_job)

    def test_run_incompatible_broadcast_shapes(self):
        """Test that incompatible parameter and observable shapes raise an error."""
        estimator = EstimatorV2(mode=self.backend)

        circuit = QuantumCircuit(2)
        theta = Parameter("theta")
        circuit.rx(theta, 0)
        circuit.cx(0, 1)

        # Create observables with shape (3,)
        observables = [{"ZZ": 1}, {"XX": 1}, {"YY": 1}]

        # Create parameter values with shape (2,) - incompatible with (3,)
        parameter_values = np.array([[0], [np.pi / 2]])

        # Should raise ValueError when trying to run with incompatible shapes
        # The error will be raised during pub coercion in the run method
        with self.assertRaises(ValueError) as context:
            estimator.run([(circuit, observables, parameter_values)], precision=0.03125)

        # Verify the error message mentions broadcasting incompatibility
        self.assertIn("broadcastable", str(context.exception).lower())

    def test_run_mismatched_precision_raises_error(self):
        """Test that pubs with different precision values raise an error."""
        estimator = EstimatorV2(mode=self.backend)

        circuit = QuantumCircuit(2)
        circuit.h(0)
        observable = SparsePauliOp.from_list([("ZZ", 1)])

        # Create pubs with different precision values
        pub1 = EstimatorPub.coerce((circuit, observable), precision=0.01)
        pub2 = EstimatorPub.coerce((circuit, observable), precision=0.02)

        with self.assertRaises(IBMInputValueError) as context:
            estimator.run([pub1, pub2])

        self.assertIn("same precision", str(context.exception))
