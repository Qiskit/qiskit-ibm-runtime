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

from pydantic import ValidationError

from qiskit_ibm_runtime.executor_sampler import SamplerV2
from qiskit_ibm_runtime.options_models.environment_options import SamplerEnvironmentOptions
from qiskit_ibm_runtime.options_models.execution_options import SamplerExecutionOptions
from qiskit_ibm_runtime.options_models.sampler_options import SamplerOptions

from ...ibm_test_case import IBMTestCase
from ...utils import get_mocked_backend


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
        """Test that image is None when experimental is empty."""
        options = SamplerOptions()
        options.experimental = {}
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

    def test_experimental_dict_execution_mapping(self):
        """Execution-related entries in `experimental.execution` must map to executor options."""
        options = SamplerOptions()
        options.experimental = {"execution": {"stretch_values": True, "scheduler_timing": True}}
        executor_options = options.to_executor_options()

        # Check that experimental dict options map to executor options.
        self.assertEqual(executor_options.execution.stretch_values, True)
        self.assertEqual(executor_options.execution.scheduler_timing, True)


class TestSamplerUsingOptions(IBMTestCase):
    """Tests option setting on the ``Sampler`` class."""

    def test_default_options(self):
        """Test that default options are set when none are provided."""
        sampler = SamplerV2(mode=get_mocked_backend())
        self.assertIsInstance(sampler.options, SamplerOptions)
        self.assertEqual(sampler.options, SamplerOptions())

    def test_options_from_instance(self):
        """Test constructing with an SamplerOptions instance."""
        opts = SamplerOptions(execution=SamplerExecutionOptions(init_qubits=False))
        sampler = SamplerV2(mode=get_mocked_backend(), options=opts)
        self.assertIs(sampler.options, opts)
        self.assertFalse(sampler.options.execution.init_qubits)

    def test_options_from_dict(self):
        """Test constructing with a nested dict."""
        opts_dict = {
            "execution": {"init_qubits": False, "rep_delay": 0.5},
            "environment": {"log_level": "DEBUG", "job_tags": ["tag1"]},
        }
        sampler = SamplerV2(mode=get_mocked_backend(), options=opts_dict)
        self.assertFalse(sampler.options.execution.init_qubits)
        self.assertEqual(sampler.options.execution.rep_delay, 0.5)
        self.assertEqual(sampler.options.environment.log_level, "DEBUG")
        self.assertEqual(sampler.options.environment.job_tags, ["tag1"])

    def test_options_from_partial_dict(self):
        """Test constructing with a nested dict when only specifying some of the options."""
        sampler = SamplerV2(
            mode=get_mocked_backend(), options={"execution": {"init_qubits": False}}
        )
        self.assertFalse(sampler.options.execution.init_qubits)
        self.assertIsNone(sampler.options.execution.rep_delay)
        self.assertEqual(sampler.options.environment, SamplerEnvironmentOptions())

    def test_options_constructor_invalid_type(self):
        """Test that an invalid options type raises TypeError."""
        with self.assertRaisesRegex(TypeError, "Expected SamplerOptions or dict"):
            SamplerV2(mode=get_mocked_backend(), options="invalid")

    def test_setter_with_instance(self):
        """Test setting options via the setter with an SamplerOptions instance."""
        sampler = SamplerV2(mode=get_mocked_backend())
        new_opts = SamplerOptions(execution=SamplerExecutionOptions(init_qubits=False))
        sampler.options = new_opts
        self.assertIs(sampler.options, new_opts)

    def test_setter_with_dict(self):
        """Test setting options via the setter with a dict."""
        sampler = SamplerV2(mode=get_mocked_backend())
        sampler.options = {"execution": {"init_qubits": False}}
        self.assertIsInstance(sampler.options, SamplerOptions)
        self.assertFalse(sampler.options.execution.init_qubits)

    def test_setter_invalid_type(self):
        """Test that setting options with an invalid type raises TypeError."""
        sampler = SamplerV2(mode=get_mocked_backend())
        with self.assertRaisesRegex(TypeError, "Expected SamplerOptions or dict"):
            sampler.options = 42

    def test_setter_replaces_options(self):
        """Test that the setter replaces (not updates) the options."""
        sampler = SamplerV2(
            mode=get_mocked_backend(), options={"environment": {"log_level": "DEBUG"}}
        )
        sampler.options = {"execution": {"init_qubits": False}}
        # environment should be back to defaults since we replaced, not updated
        self.assertEqual(sampler.options.environment.log_level, "WARNING")
        self.assertFalse(sampler.options.execution.init_qubits)

    def test_experimental_options_default_empty(self):
        """Test that experimental options default to empty dict."""
        sampler = SamplerV2(mode=get_mocked_backend())
        self.assertEqual(sampler.options.experimental, {})

    def test_experimental_options_from_dict(self):
        """Test constructing with experimental options in dict."""
        opts_dict = {"experimental": {"foo": "bar", "baz": 123}}
        sampler = SamplerV2(mode=get_mocked_backend(), options=opts_dict)
        self.assertEqual(sampler.options.experimental, {"foo": "bar", "baz": 123})

    def test_experimental_options_from_instance(self):
        """Test constructing with an SamplerOptions instance with experimental options."""
        opts = SamplerOptions(experimental={"custom_key": "custom_value"})
        sampler = SamplerV2(mode=get_mocked_backend(), options=opts)
        self.assertEqual(sampler.options.experimental, {"custom_key": "custom_value"})

    def test_experimental_options_setter(self):
        """Test setting experimental options via the setter."""
        sampler = SamplerV2(mode=get_mocked_backend())
        sampler.options = {"experimental": {"test": "value"}}
        self.assertEqual(sampler.options.experimental, {"test": "value"})

    def test_validation_on_mutation(self):
        """Test validation errors are raised on mutation, not just construction."""
        options = SamplerExecutionOptions(init_qubits=False)
        with self.assertRaises(ValidationError):
            options.init_qubits = [0, 1]

    def test_extra_variables_are_forbidden(self):
        """Test that we can not set variables undefined by the model."""
        options = SamplerExecutionOptions()
        with self.assertRaises(ValidationError):
            options.not_a_variable = 0
