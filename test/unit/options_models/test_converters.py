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

"""Tests the converters for options models."""

from qiskit_ibm_runtime.options_models.converters import (
    estimator_options_to_executor_options,
    sampler_option_to_executor_options,
)
from qiskit_ibm_runtime.options_models.estimator import EstimatorOptions
from qiskit_ibm_runtime.options_models.sampler import SamplerOptions

from ...ibm_test_case import IBMTestCase


class TestSamplerOptionsToExecutorOptions(IBMTestCase):
    """Tests for SamplerOptions to ExecutorOptions method."""

    def test_default_options_mapping(self):
        """Test that default options are correctly mapped."""
        options = SamplerOptions()
        executor_options = sampler_option_to_executor_options(options)

        # Check default execution options
        self.assertEqual(executor_options.execution.init_qubits, True)
        self.assertIsNone(executor_options.execution.rep_delay)

        # Check default environment options
        self.assertEqual(executor_options.environment.log_level, "WARNING")
        self.assertEqual(executor_options.environment.job_tags, [])
        self.assertEqual(executor_options.environment.private, False)
        self.assertIsNone(executor_options.environment.max_execution_time)
        self.assertIsNone(executor_options.environment.image)

    def test_all_options_mapping(self):
        """Test mapping of all supported options together."""
        options = SamplerOptions()
        options.execution.init_qubits = False
        options.execution.rep_delay = 0.0002
        options.environment.log_level = "INFO"
        options.environment.job_tags = ["test1", "test2"]
        options.environment.private = True
        options.max_execution_time = 300
        options.experimental = {"image": "test-image:latest"}

        executor_options = sampler_option_to_executor_options(options)

        self.assertEqual(executor_options.execution.init_qubits, False)
        self.assertEqual(executor_options.execution.rep_delay, 0.0002)
        self.assertEqual(executor_options.environment.log_level, "INFO")
        self.assertEqual(executor_options.environment.job_tags, ["test1", "test2"])
        self.assertEqual(executor_options.environment.private, True)
        self.assertEqual(executor_options.environment.max_execution_time, 300)
        self.assertEqual(executor_options.environment.image, "test-image:latest")

    def test_experimental_image_not_set(self):
        """Test that image is None when experimental is empty."""
        options = SamplerOptions()
        options.experimental = {}
        executor_options = sampler_option_to_executor_options(options)

        self.assertIsNone(executor_options.environment.image)

    def test_experimental_dict_carry_over(self):
        """Test that experimental dict is carried over to executor options."""
        options = SamplerOptions()
        options.experimental = {
            "custom_key": 123,
            "image": "test:v1",
            "execution": {"stretch_values": True, "scheduler_timing": True},
        }
        executor_options = sampler_option_to_executor_options(options)

        # Experimental dict should be carried over.
        self.assertEqual(options.experimental, executor_options.experimental)

        # `image` and execution-related entries must map to executor options.
        self.assertEqual(executor_options.environment.image, "test:v1")
        self.assertEqual(executor_options.execution.stretch_values, True)
        self.assertEqual(executor_options.execution.scheduler_timing, True)


class TestEstimatorOptionsToExecutorOptions(IBMTestCase):
    """Tests for EstimatorOptions to ExecutorOptions method."""

    def test_to_executor_options(self):
        """Test conversion to ExecutorOptions."""
        options = EstimatorOptions(
            default_precision=0.022097,
            max_execution_time=300,
        )
        options.execution.init_qubits = True
        options.execution.rep_delay = 0.001

        executor_options = estimator_options_to_executor_options(options)

        self.assertTrue(executor_options.execution.init_qubits)
        self.assertEqual(executor_options.execution.rep_delay, 0.001)
        self.assertEqual(executor_options.environment.max_execution_time, 300)

    def test_to_executor_options_with_experimental(self):
        """Test conversion with experimental options."""
        options = EstimatorOptions()
        options.experimental = {"image": "custom:image", "other": "value"}

        executor_options = estimator_options_to_executor_options(options)

        self.assertEqual(executor_options.environment.image, "custom:image")
        self.assertEqual(executor_options.experimental, options.experimental)
