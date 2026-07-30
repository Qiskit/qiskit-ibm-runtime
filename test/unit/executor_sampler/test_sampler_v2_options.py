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

"""Tests for SamplerOptions to ExecutorOptions mapping method."""

from pydantic import ValidationError

from qiskit_ibm_runtime.executor_sampler import SamplerV2
from qiskit_ibm_runtime.fake_provider import FakeBrisbane
from qiskit_ibm_runtime.options_models.environment import SamplerEnvironmentOptions
from qiskit_ibm_runtime.options_models.execution import SamplerExecutionOptions
from qiskit_ibm_runtime.options_models.sampler import SamplerOptions

from ...ibm_test_case import IBMTestCase


class TestSamplerUsingOptions(IBMTestCase):
    """Tests option setting on the ``Sampler`` class."""

    def test_default_options(self):
        """Test that default options are set when none are provided."""
        sampler = SamplerV2(mode=FakeBrisbane())
        self.assertIsInstance(sampler.options, SamplerOptions)
        self.assertEqual(sampler.options, SamplerOptions())

    def test_options_from_instance(self):
        """Test constructing with an SamplerOptions instance."""
        opts = SamplerOptions(execution=SamplerExecutionOptions(init_qubits=False))
        sampler = SamplerV2(mode=FakeBrisbane(), options=opts)
        self.assertIs(sampler.options, opts)
        self.assertFalse(sampler.options.execution.init_qubits)

    def test_options_from_dict(self):
        """Test constructing with a nested dict."""
        opts_dict = {
            "execution": {"init_qubits": False, "rep_delay": 0.5},
            "environment": {"log_level": "DEBUG", "job_tags": ["tag1"]},
        }
        sampler = SamplerV2(mode=FakeBrisbane(), options=opts_dict)
        self.assertFalse(sampler.options.execution.init_qubits)
        self.assertEqual(sampler.options.execution.rep_delay, 0.5)
        self.assertEqual(sampler.options.environment.log_level, "DEBUG")
        self.assertEqual(sampler.options.environment.job_tags, ["tag1"])

    def test_options_from_partial_dict(self):
        """Test constructing with a nested dict when only specifying some of the options."""
        sampler = SamplerV2(mode=FakeBrisbane(), options={"execution": {"init_qubits": False}})
        self.assertFalse(sampler.options.execution.init_qubits)
        self.assertIsNone(sampler.options.execution.rep_delay)
        self.assertEqual(sampler.options.environment, SamplerEnvironmentOptions())

    def test_options_constructor_invalid_type(self):
        """Test that an invalid options type raises TypeError."""
        with self.assertRaisesRegex(TypeError, "Expected SamplerOptions or dict"):
            SamplerV2(mode=FakeBrisbane(), options="invalid")

    def test_setter_with_instance(self):
        """Test setting options via the setter with an SamplerOptions instance."""
        sampler = SamplerV2(mode=FakeBrisbane())
        new_opts = SamplerOptions(execution=SamplerExecutionOptions(init_qubits=False))
        sampler.options = new_opts
        self.assertIs(sampler.options, new_opts)

    def test_setter_with_dict(self):
        """Test setting options via the setter with a dict."""
        sampler = SamplerV2(mode=FakeBrisbane())
        sampler.options = {"execution": {"init_qubits": False}}
        self.assertIsInstance(sampler.options, SamplerOptions)
        self.assertFalse(sampler.options.execution.init_qubits)

    def test_setter_invalid_type(self):
        """Test that setting options with an invalid type raises TypeError."""
        sampler = SamplerV2(mode=FakeBrisbane())
        with self.assertRaisesRegex(TypeError, "Expected SamplerOptions or dict"):
            sampler.options = 42

    def test_setter_replaces_options(self):
        """Test that the setter replaces (not updates) the options."""
        sampler = SamplerV2(mode=FakeBrisbane(), options={"environment": {"log_level": "DEBUG"}})
        sampler.options = {"execution": {"init_qubits": False}}
        # environment should be back to defaults since we replaced, not updated
        self.assertEqual(sampler.options.environment.log_level, "WARNING")
        self.assertFalse(sampler.options.execution.init_qubits)

    def test_experimental_options_default_empty(self):
        """Test that experimental options default to empty dict."""
        sampler = SamplerV2(mode=FakeBrisbane())
        self.assertEqual(sampler.options.experimental, {})

    def test_experimental_options_from_dict(self):
        """Test constructing with experimental options in dict."""
        opts_dict = {"experimental": {"foo": "bar", "baz": 123}}
        sampler = SamplerV2(mode=FakeBrisbane(), options=opts_dict)
        self.assertEqual(sampler.options.experimental, {"foo": "bar", "baz": 123})

    def test_experimental_options_from_instance(self):
        """Test constructing with an SamplerOptions instance with experimental options."""
        opts = SamplerOptions(experimental={"custom_key": "custom_value"})
        sampler = SamplerV2(mode=FakeBrisbane(), options=opts)
        self.assertEqual(sampler.options.experimental, {"custom_key": "custom_value"})

    def test_experimental_options_setter(self):
        """Test setting experimental options via the setter."""
        sampler = SamplerV2(mode=FakeBrisbane())
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
