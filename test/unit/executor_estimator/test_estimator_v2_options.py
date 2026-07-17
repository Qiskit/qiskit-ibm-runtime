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

"""Unit tests for EstimatorV2 options."""

from pydantic import ValidationError

from qiskit_ibm_runtime.executor_estimator.estimator import EstimatorV2
from qiskit_ibm_runtime.fake_provider import FakeBrisbane
from qiskit_ibm_runtime.options_models.environment import EnvironmentOptions
from qiskit_ibm_runtime.options_models.estimator import EstimatorOptions
from qiskit_ibm_runtime.options_models.execution import ExecutionOptions

from ...ibm_test_case import IBMTestCase


class TestEstimatorUsingOptions(IBMTestCase):
    """Tests option setting on the ``Estimator`` class."""

    def test_default_options(self):
        """Test that default options are set when none are provided."""
        estimator = EstimatorV2(mode=FakeBrisbane())
        self.assertIsInstance(estimator.options, EstimatorOptions)
        self.assertEqual(estimator.options, EstimatorOptions())

    def test_options_from_instance(self):
        """Test constructing with an EstimatorOptions instance."""
        opts = EstimatorOptions(execution=ExecutionOptions(init_qubits=False))
        estimator = EstimatorV2(mode=FakeBrisbane(), options=opts)
        self.assertIs(estimator.options, opts)
        self.assertFalse(estimator.options.execution.init_qubits)

    def test_options_from_dict(self):
        """Test constructing with a nested dict."""
        opts_dict = {
            "execution": {"init_qubits": False, "rep_delay": 0.5},
            "environment": {"log_level": "DEBUG", "job_tags": ["tag1"]},
        }
        estimator = EstimatorV2(mode=FakeBrisbane(), options=opts_dict)
        self.assertFalse(estimator.options.execution.init_qubits)
        self.assertEqual(estimator.options.execution.rep_delay, 0.5)
        self.assertEqual(estimator.options.environment.log_level, "DEBUG")
        self.assertEqual(estimator.options.environment.job_tags, ["tag1"])

    def test_options_from_partial_dict(self):
        """Test constructing with a nested dict when only specifying some of the options."""
        estimator = EstimatorV2(mode=FakeBrisbane(), options={"execution": {"init_qubits": False}})
        self.assertFalse(estimator.options.execution.init_qubits)
        self.assertIsNone(estimator.options.execution.rep_delay)
        self.assertEqual(estimator.options.environment, EnvironmentOptions())

    def test_options_constructor_invalid_type(self):
        """Test that an invalid options type raises TypeError."""
        with self.assertRaisesRegex(TypeError, "Expected EstimatorOptions or dict"):
            EstimatorV2(mode=FakeBrisbane(), options="invalid")

    def test_setter_with_instance(self):
        """Test setting options via the setter with an EstimatorOptions instance."""
        estimator = EstimatorV2(mode=FakeBrisbane())
        new_opts = EstimatorOptions(execution=ExecutionOptions(init_qubits=False))
        estimator.options = new_opts
        self.assertIs(estimator.options, new_opts)

    def test_setter_with_dict(self):
        """Test setting options via the setter with a dict."""
        estimator = EstimatorV2(mode=FakeBrisbane())
        estimator.options = {"execution": {"init_qubits": False}}
        self.assertIsInstance(estimator.options, EstimatorOptions)
        self.assertFalse(estimator.options.execution.init_qubits)

    def test_setter_invalid_type(self):
        """Test that setting options with an invalid type raises TypeError."""
        estimator = EstimatorV2(mode=FakeBrisbane())
        with self.assertRaisesRegex(TypeError, "Expected EstimatorOptions or dict"):
            estimator.options = 42

    def test_setter_replaces_options(self):
        """Test that the setter replaces (not updates) the options."""
        estimator = EstimatorV2(
            mode=FakeBrisbane(), options={"environment": {"log_level": "DEBUG"}}
        )
        estimator.options = {"execution": {"init_qubits": False}}
        # environment should be back to defaults since we replaced, not updated
        self.assertEqual(estimator.options.environment.log_level, "WARNING")
        self.assertFalse(estimator.options.execution.init_qubits)

    def test_experimental_options_default_empty(self):
        """Test that experimental options default to empty dict."""
        estimator = EstimatorV2(mode=FakeBrisbane())
        self.assertEqual(estimator.options.experimental, {})

    def test_experimental_options_from_dict(self):
        """Test constructing with experimental options in dict."""
        opts_dict = {"experimental": {"foo": "bar", "baz": 123}}
        estimator = EstimatorV2(mode=FakeBrisbane(), options=opts_dict)
        self.assertEqual(estimator.options.experimental, {"foo": "bar", "baz": 123})

    def test_experimental_options_from_instance(self):
        """Test constructing with an EstimatorOptions instance with experimental options."""
        opts = EstimatorOptions(experimental={"custom_key": "custom_value"})
        estimator = EstimatorV2(mode=FakeBrisbane(), options=opts)
        self.assertEqual(estimator.options.experimental, {"custom_key": "custom_value"})

    def test_experimental_options_setter(self):
        """Test setting experimental options via the setter."""
        estimator = EstimatorV2(mode=FakeBrisbane())
        estimator.options = {"experimental": {"test": "value"}}
        self.assertEqual(estimator.options.experimental, {"test": "value"})

    def test_validation_on_mutation(self):
        """Test validation errors are raised on mutation, not just construction."""
        options = ExecutionOptions(init_qubits=False)
        with self.assertRaises(ValidationError):
            options.init_qubits = [0, 1]

    def test_extra_variables_are_forbidden(self):
        """Test that we can not set variables undefined by the model."""
        options = ExecutionOptions()
        with self.assertRaises(ValidationError):
            options.not_a_variable = 0
