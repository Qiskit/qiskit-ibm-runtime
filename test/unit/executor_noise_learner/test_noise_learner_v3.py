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

"""Tests for client-side noise learner."""

from unittest.mock import MagicMock, patch

from ddt import ddt
from qiskit import QuantumCircuit

from qiskit_ibm_runtime import Executor, QuantumProgram
from qiskit_ibm_runtime.executor_noise_learner import NoiseLearnerV3
from qiskit_ibm_runtime.runtime_job_v2 import RuntimeJobV2

from ...ibm_test_case import IBMTestCase
from ...utils import get_mocked_backend


@ddt
class TestNoiseLearnerV3(IBMTestCase):
    """Tests the ``NoiseLearnerV3`` class."""

    def setUp(self):
        """Set up test fixtures."""
        self.backend = get_mocked_backend()

        # Create a mock job to return from executor.run()
        self.mock_job = MagicMock(spec=RuntimeJobV2)
        self.mock_job.job_id.return_value = "test-job-id"

        # Patch Executor
        self.executor_patcher = patch(
            "qiskit_ibm_runtime.executor_noise_learner.noise_learner_v3.Executor"
        )
        self.mock_executor_class = self.executor_patcher.start()

        # Create mock executor instance
        self.mock_executor_instance = MagicMock(spec=Executor)
        self.mock_executor_instance._backend = self.backend
        self.mock_executor_instance.run = MagicMock(return_value=self.mock_job)
        self.mock_executor_class.return_value = self.mock_executor_instance

    def tearDown(self):
        """Clean up patches."""
        self.executor_patcher.stop()

    def test_run(self):
        """Test run with single pub without parameters."""
        noise_learner = NoiseLearnerV3(mode=self.backend)

        circuit = QuantumCircuit(2)
        circuit.h(0)
        circuit.cx(0, 1)

        job = noise_learner.run([circuit])

        # Verify executor.run was called
        self.mock_executor_instance.run.assert_called_once()

        # Verify the quantum program passed to executor
        call_args = self.mock_executor_instance.run.call_args
        quantum_program = call_args[0][0]
        self.assertIsInstance(quantum_program, QuantumProgram)

        # Verify that information needed for post-processing dispatch were attached
        self.assertEqual(quantum_program._semantic_role, "noise_learner_v3")

        # Verify job was returned
        self.assertEqual(job, self.mock_job)
