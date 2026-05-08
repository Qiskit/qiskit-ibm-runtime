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

"""Tests for SamplerOptions.to_executor_options() mapping method."""

import unittest

from qiskit_ibm_runtime.options_models import SamplerOptions


class TestSamplerOptionsToExecutorOptions(unittest.TestCase):
    """Tests for SamplerOptions.to_executor_options() method."""

    def test_default_options_mapping(self):
        """Test that default options are correctly mapped."""
        options = SamplerOptions()
        executor_options = options.to_executor_options()

        # Check default execution options
        self.assertEqual(executor_options.execution.init_qubits, True)
        self.assertIsNone(executor_options.execution.rep_delay)

        # Check default environment options
        self.assertEqual(executor_options.environment.log_level, "WARNING")
        self.assertEqual(executor_options.environment.job_tags, [])
        self.assertEqual(executor_options.environment.private, False)
        self.assertIsNone(executor_options.environment.max_execution_time)
        self.assertIsNone(executor_options.environment.image)

    def test_experimental_image_not_set(self):
        """Test that image is None when experimental is None."""
        options = SamplerOptions()
        options.experimental = None
        executor_options = options.to_executor_options()

        self.assertIsNone(executor_options.environment.image)

    def test_experimental_other_keys_ignored(self):
        """Test that other experimental keys don't affect mapping."""
        options = SamplerOptions()
        options.experimental = {"image": "test:v1", "other_key": "value"}
        executor_options = options.to_executor_options()

        # Only image should be mapped
        self.assertEqual(executor_options.environment.image, "test:v1")

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

        executor_options = options.to_executor_options()

        self.assertEqual(executor_options.execution.init_qubits, False)
        self.assertEqual(executor_options.execution.rep_delay, 0.0002)
        self.assertEqual(executor_options.environment.log_level, "INFO")
        self.assertEqual(executor_options.environment.job_tags, ["test1", "test2"])
        self.assertEqual(executor_options.environment.private, True)
        self.assertEqual(executor_options.environment.max_execution_time, 300)
        self.assertEqual(executor_options.environment.image, "test-image:latest")

    def test_experimental_dict_carry_over(self):
        """Test that experimental dict is carried over to executor options."""
        options = SamplerOptions()
        options.experimental = {"custom_key": "custom_value", "another_key": 123}
        executor_options = options.to_executor_options()

        # Check that experimental dict is carried over
        self.assertEqual(executor_options.experimental["custom_key"], "custom_value")
        self.assertEqual(executor_options.experimental["another_key"], 123)
