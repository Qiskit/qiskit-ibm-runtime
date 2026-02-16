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

"""Tests for SamplerV2 options handling

both setting the SamplerV2 object, and mapping to executor when .run is called.
"""

import unittest
from unittest.mock import MagicMock, patch
from ddt import ddt, data

from qiskit import QuantumCircuit

from qiskit_ibm_runtime.executor.routines.sampler_v2 import SamplerV2
from qiskit_ibm_runtime.executor.routines.sampler_v2.options import SamplerOptions
from qiskit_ibm_runtime.ibm_backend import IBMBackend


def create_mock_backend():
    """Create a mock IBMBackend for testing."""
    backend = MagicMock(spec=IBMBackend)
    backend.name = "fake_backend"
    backend._instance = "ibm-q/open/main"
    service = MagicMock()
    backend.service = service
    return backend


@ddt
class TestSamplerV2Options(unittest.TestCase):
    """Tests for SamplerV2 options handling."""

    def setUp(self):
        """Set up test fixtures."""
        self.backend = create_mock_backend()
        self.circuit = QuantumCircuit(1, 1)
        self.circuit.h(0)
        self.circuit.measure_all()

    @patch("qiskit_ibm_runtime.executor.routines.sampler_v2.sampler.Executor.run")
    def test_default_options_mapping(self, mock_run):
        """Test that default options are correctly mapped to executor."""
        mock_run.return_value = MagicMock()

        # Create sampler with no options specified
        sampler = SamplerV2(mode=self.backend)
        sampler.run([self.circuit])

        # Verify executor.run was called
        self.assertEqual(mock_run.call_count, 1)

        # Verify the executor's options were set correctly
        executor_options = sampler._executor.options

        # Check default execution options
        self.assertEqual(executor_options.execution.init_qubits, True)
        self.assertIsNone(executor_options.execution.rep_delay)

        # Check default environment options
        self.assertEqual(executor_options.environment.log_level, "WARNING")
        self.assertEqual(executor_options.environment.job_tags, [])
        self.assertEqual(executor_options.environment.private, False)
        self.assertIsNone(executor_options.environment.max_execution_time)
        self.assertIsNone(executor_options.environment.image)

    @patch("qiskit_ibm_runtime.executor.routines.sampler_v2.sampler.Executor.run")
    def test_default_shots(self, mock_run):
        """Test that default shots are used when not specified."""
        mock_run.return_value = MagicMock()

        sampler = SamplerV2(mode=self.backend)
        expected_default_shots = sampler.options.default_shots
        sampler.run([self.circuit])

        quantum_program = mock_run.call_args[0][0]
        self.assertEqual(quantum_program.shots, expected_default_shots)

    @patch("qiskit_ibm_runtime.executor.routines.sampler_v2.sampler.Executor.run")
    def test_custom_default_shots(self, mock_run):
        """Test setting custom default_shots in options."""
        mock_run.return_value = MagicMock()

        sampler = SamplerV2(mode=self.backend)
        sampler.options.default_shots = 2048
        sampler.run([self.circuit])

        quantum_program = mock_run.call_args[0][0]
        self.assertEqual(quantum_program.shots, 2048)

    @data(True, False)
    @patch("qiskit_ibm_runtime.executor.routines.sampler_v2.sampler.Executor.run")
    def test_execution_init_qubits(self, init_qubits_value, mock_run):
        """Test setting execution.init_qubits to different values."""
        mock_run.return_value = MagicMock()

        sampler = SamplerV2(mode=self.backend)
        sampler.options.execution.init_qubits = init_qubits_value
        sampler.run([self.circuit])

        executor_options = sampler._executor.options
        self.assertEqual(executor_options.execution.init_qubits, init_qubits_value)

    @patch("qiskit_ibm_runtime.executor.routines.sampler_v2.sampler.Executor.run")
    def test_execution_rep_delay_set(self, mock_run):
        """Test setting execution.rep_delay to a specific value."""
        mock_run.return_value = MagicMock()

        sampler = SamplerV2(mode=self.backend)
        sampler.options.execution.rep_delay = 0.0001
        sampler.run([self.circuit])

        executor_options = sampler._executor.options
        self.assertEqual(executor_options.execution.rep_delay, 0.0001)

    @data("classified", "kerneled", "avg_kerneled")
    @patch("qiskit_ibm_runtime.executor.routines.sampler_v2.sampler.Executor.run")
    def test_execution_meas_type(self, meas_type_value, mock_run):
        """Test setting execution.meas_type to different values."""
        mock_run.return_value = MagicMock()

        sampler = SamplerV2(mode=self.backend)
        sampler.options.execution.meas_type = meas_type_value
        sampler.run([self.circuit])

        quantum_program = mock_run.call_args[0][0]
        self.assertEqual(quantum_program.meas_level, meas_type_value)

    @patch("qiskit_ibm_runtime.executor.routines.sampler_v2.sampler.Executor.run")
    def test_execution_meas_type_unset(self, mock_run):
        """Test that execution.meas_type is None when not set."""
        mock_run.return_value = MagicMock()

        sampler = SamplerV2(mode=self.backend)
        sampler.run([self.circuit])

        quantum_program = mock_run.call_args[0][0]
        self.assertIsNone(quantum_program.meas_level)

    @patch("qiskit_ibm_runtime.executor.routines.sampler_v2.sampler.Executor.run")
    def test_environment_log_level(self, mock_run):
        """Test setting environment.log_level to different values."""
        mock_run.return_value = MagicMock()

        sampler = SamplerV2(mode=self.backend)
        sampler.options.environment.log_level = "DEBUG"
        sampler.run([self.circuit])

        executor_options = sampler._executor.options
        self.assertEqual(executor_options.environment.log_level, "DEBUG")

    @patch("qiskit_ibm_runtime.executor.routines.sampler_v2.sampler.Executor.run")
    def test_environment_job_tags_set(self, mock_run):
        """Test setting environment.job_tags."""
        mock_run.return_value = MagicMock()

        sampler = SamplerV2(mode=self.backend)
        sampler.options.environment.job_tags = ["test", "sampler_v2"]
        sampler.run([self.circuit])

        executor_options = sampler._executor.options
        self.assertEqual(executor_options.environment.job_tags, ["test", "sampler_v2"])

    @data(True, False)
    @patch("qiskit_ibm_runtime.executor.routines.sampler_v2.sampler.Executor.run")
    def test_environment_private(self, private_value, mock_run):
        """Test setting environment.private to different values."""
        mock_run.return_value = MagicMock()

        sampler = SamplerV2(mode=self.backend)
        sampler.options.environment.private = private_value
        sampler.run([self.circuit])

        executor_options = sampler._executor.options
        self.assertEqual(executor_options.environment.private, private_value)

    @patch("qiskit_ibm_runtime.executor.routines.sampler_v2.sampler.Executor.run")
    def test_max_execution_time_set(self, mock_run):
        """Test setting max_execution_time."""
        mock_run.return_value = MagicMock()

        sampler = SamplerV2(mode=self.backend)
        sampler.options.max_execution_time = 600
        sampler.run([self.circuit])

        executor_options = sampler._executor.options
        self.assertEqual(executor_options.environment.max_execution_time, 600)

    @patch("qiskit_ibm_runtime.executor.routines.sampler_v2.sampler.Executor.run")
    def test_experimental_image_set(self, mock_run):
        """Test setting experimental.image."""
        mock_run.return_value = MagicMock()

        sampler = SamplerV2(mode=self.backend)
        sampler.options.experimental = {"image": "custom-runtime-image:latest"}
        sampler.run([self.circuit])

        executor_options = sampler._executor.options
        self.assertEqual(executor_options.environment.image, "custom-runtime-image:latest")

    @patch("qiskit_ibm_runtime.executor.routines.sampler_v2.sampler.Executor.run")
    def test_dynamical_decoupling_enable_raises_error(self, mock_run):
        """Test that enabling dynamical_decoupling raises NotImplementedError."""
        sampler = SamplerV2(mode=self.backend)
        sampler.options.dynamical_decoupling.enable = True

        with self.assertRaises(NotImplementedError) as context:
            sampler.run([self.circuit])

        self.assertIn("Dynamical decoupling", str(context.exception))
        mock_run.assert_not_called()

    @patch("qiskit_ibm_runtime.executor.routines.sampler_v2.sampler.Executor.run")
    def test_twirling_enable_gates_raises_error(self, mock_run):
        """Test that enabling twirling.enable_gates raises NotImplementedError."""
        sampler = SamplerV2(mode=self.backend)
        sampler.options.twirling.enable_gates = True

        with self.assertRaises(NotImplementedError) as context:
            sampler.run([self.circuit])

        self.assertIn("Twirling", str(context.exception))
        mock_run.assert_not_called()

    @patch("qiskit_ibm_runtime.executor.routines.sampler_v2.sampler.Executor.run")
    def test_twirling_enable_measure_raises_error(self, mock_run):
        """Test that enabling twirling.enable_measure raises NotImplementedError."""
        sampler = SamplerV2(mode=self.backend)
        sampler.options.twirling.enable_measure = True

        with self.assertRaises(NotImplementedError) as context:
            sampler.run([self.circuit])

        self.assertIn("Twirling", str(context.exception))
        mock_run.assert_not_called()

    @patch("qiskit_ibm_runtime.executor.routines.sampler_v2.sampler.Executor.run")
    def test_twirling_both_enabled_raises_error(self, mock_run):
        """Test that enabling both twirling options raises NotImplementedError."""
        sampler = SamplerV2(mode=self.backend)
        sampler.options.twirling.enable_gates = True
        sampler.options.twirling.enable_measure = True

        with self.assertRaises(NotImplementedError) as context:
            sampler.run([self.circuit])

        self.assertIn("Twirling", str(context.exception))
        mock_run.assert_not_called()

    @patch("qiskit_ibm_runtime.executor.routines.sampler_v2.sampler.Executor.run")
    def test_experimental_other_than_image_raises_error(self, mock_run):
        """Test that experimental options other than 'image' raise NotImplementedError."""
        sampler = SamplerV2(mode=self.backend)
        sampler.options.experimental = {"custom_option": "value"}

        with self.assertRaises(NotImplementedError) as context:
            sampler.run([self.circuit])

        self.assertIn("Experimental options", str(context.exception))
        mock_run.assert_not_called()

    def test_options_initialization_with_dict(self):
        """Test that options can be initialized with a dict."""
        options_dict = {
            "default_shots": 2048,
        }
        sampler = SamplerV2(mode=self.backend, options=options_dict)

        self.assertIsInstance(sampler.options, SamplerOptions)
        self.assertEqual(sampler.options.default_shots, 2048)

    def test_options_initialization_with_sampler_options(self):
        """Test that options can be initialized with SamplerOptions instance."""
        options = SamplerOptions()
        options.default_shots = 8192

        sampler = SamplerV2(mode=self.backend, options=options)

        self.assertIs(sampler.options, options)
        self.assertEqual(sampler.options.default_shots, 8192)

    @patch("qiskit_ibm_runtime.executor.routines.sampler_v2.sampler.Executor.run")
    def test_multiple_execution_options(self, mock_run):
        """Test setting multiple execution options together."""
        mock_run.return_value = MagicMock()

        sampler = SamplerV2(mode=self.backend)
        sampler.options.execution.init_qubits = False
        sampler.options.execution.rep_delay = 0.0002
        sampler.options.execution.meas_type = "kerneled"
        sampler.run([self.circuit])

        executor_options = sampler._executor.options
        self.assertEqual(executor_options.execution.init_qubits, False)
        self.assertEqual(executor_options.execution.rep_delay, 0.0002)

        quantum_program = mock_run.call_args[0][0]
        self.assertEqual(quantum_program.meas_level, "kerneled")

    @patch("qiskit_ibm_runtime.executor.routines.sampler_v2.sampler.Executor.run")
    def test_multiple_environment_options(self, mock_run):
        """Test setting multiple environment options together."""
        mock_run.return_value = MagicMock()

        sampler = SamplerV2(mode=self.backend)
        sampler.options.environment.log_level = "INFO"
        sampler.options.environment.job_tags = ["test1", "test2"]
        sampler.options.environment.private = True
        sampler.options.max_execution_time = 300
        sampler.run([self.circuit])

        executor_options = sampler._executor.options
        self.assertEqual(executor_options.environment.log_level, "INFO")
        self.assertEqual(executor_options.environment.job_tags, ["test1", "test2"])
        self.assertEqual(executor_options.environment.private, True)
        self.assertEqual(executor_options.environment.max_execution_time, 300)

    @patch("qiskit_ibm_runtime.executor.routines.sampler_v2.sampler.Executor.run")
    def test_all_supported_options_together(self, mock_run):
        """Test setting all supported options together."""
        mock_run.return_value = MagicMock()

        sampler = SamplerV2(mode=self.backend)
        sampler.options.default_shots = 1024
        sampler.options.execution.init_qubits = False
        sampler.options.execution.rep_delay = 0.0003
        sampler.options.execution.meas_type = "avg_kerneled"
        sampler.options.environment.log_level = "DEBUG"
        sampler.options.environment.job_tags = ["comprehensive", "test"]
        sampler.options.environment.private = True
        sampler.options.max_execution_time = 900
        sampler.options.experimental = {"image": "test-image:v1"}
        sampler.run([self.circuit])

        # Verify quantum program
        quantum_program = mock_run.call_args[0][0]
        self.assertEqual(quantum_program.shots, 1024)
        self.assertEqual(quantum_program.meas_level, "avg_kerneled")

        # Verify executor options
        executor_options = sampler._executor.options
        self.assertEqual(executor_options.execution.init_qubits, False)
        self.assertEqual(executor_options.execution.rep_delay, 0.0003)
        self.assertEqual(executor_options.environment.log_level, "DEBUG")
        self.assertEqual(executor_options.environment.job_tags, ["comprehensive", "test"])
        self.assertEqual(executor_options.environment.private, True)
        self.assertEqual(executor_options.environment.max_execution_time, 900)
        self.assertEqual(executor_options.environment.image, "test-image:v1")
