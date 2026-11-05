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

"""Tests for setting Estimator options."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from qiskit_ibm_runtime.executor_estimator.estimator import Estimator
from qiskit_ibm_runtime.fake_provider import FakeBrisbane
from qiskit_ibm_runtime.options_models.environment import EnvironmentOptions
from qiskit_ibm_runtime.options_models.estimator import EstimatorOptions
from qiskit_ibm_runtime.options_models.execution import ExecutionOptions


class TestEstimatorUsingOptions:
    """Tests option setting on the ``Estimator`` class."""

    def test_default_options(self) -> None:
        """Test that default options are set when none are provided."""
        estimator = Estimator(mode=FakeBrisbane())
        assert isinstance(estimator.options, EstimatorOptions)
        assert estimator.options == EstimatorOptions()

    def test_options_from_instance(self) -> None:
        """Test constructing with an EstimatorOptions instance."""
        opts = EstimatorOptions(execution=ExecutionOptions(init_qubits=False))
        estimator = Estimator(mode=FakeBrisbane(), options=opts)
        assert estimator.options is opts
        assert not estimator.options.execution.init_qubits

    def test_options_from_dict(self) -> None:
        """Test constructing with a nested dict."""
        opts_dict = {
            "execution": {"init_qubits": False, "rep_delay": 0.5},
            "environment": {"log_level": "DEBUG", "job_tags": ["tag1"]},
        }
        estimator = Estimator(mode=FakeBrisbane(), options=opts_dict)
        assert not estimator.options.execution.init_qubits
        assert estimator.options.execution.rep_delay == 0.5
        assert estimator.options.environment.log_level == "DEBUG"
        assert estimator.options.environment.job_tags == ["tag1"]

    def test_options_from_partial_dict(self) -> None:
        """Test constructing with a nested dict when only specifying some of the options."""
        estimator = Estimator(mode=FakeBrisbane(), options={"execution": {"init_qubits": False}})
        assert not estimator.options.execution.init_qubits
        assert estimator.options.execution.rep_delay is None
        assert estimator.options.environment == EnvironmentOptions()

    def test_options_constructor_invalid_type(self) -> None:
        """Test that an invalid options type raises TypeError."""
        with pytest.raises(TypeError, match="Expected EstimatorOptions or dict"):
            Estimator(mode=FakeBrisbane(), options="invalid")  # type: ignore[arg-type]

    def test_setter_with_instance(self) -> None:
        """Test setting options via the setter with an EstimatorOptions instance."""
        estimator = Estimator(mode=FakeBrisbane())
        new_opts = EstimatorOptions(execution=ExecutionOptions(init_qubits=False))
        estimator.options = new_opts
        assert estimator.options is new_opts

    def test_setter_with_dict(self) -> None:
        """Test setting options via the setter with a dict."""
        estimator = Estimator(mode=FakeBrisbane())
        estimator.options = {"execution": {"init_qubits": False}}  # type: ignore[assignment]
        assert isinstance(estimator.options, EstimatorOptions)
        assert not estimator.options.execution.init_qubits

    def test_setter_invalid_type(self) -> None:
        """Test that setting options with an invalid type raises TypeError."""
        estimator = Estimator(mode=FakeBrisbane())
        with pytest.raises(TypeError, match="Expected EstimatorOptions or dict"):
            estimator.options = 42  # type: ignore[assignment]

    def test_setter_replaces_options(self) -> None:
        """Test that the setter replaces (not updates) the options."""
        estimator = Estimator(mode=FakeBrisbane(), options={"environment": {"log_level": "DEBUG"}})
        estimator.options = {"execution": {"init_qubits": False}}  # type: ignore[assignment]
        # environment should be back to defaults since we replaced, not updated
        assert estimator.options.environment.log_level == "WARNING"
        assert not estimator.options.execution.init_qubits

    def test_experimental_options_default_empty(self) -> None:
        """Test that experimental options default to empty dict."""
        estimator = Estimator(mode=FakeBrisbane())
        assert estimator.options.experimental == {}

    def test_experimental_options_from_dict(self) -> None:
        """Test constructing with experimental options in dict."""
        opts_dict = {"experimental": {"foo": "bar", "baz": 123}}
        estimator = Estimator(mode=FakeBrisbane(), options=opts_dict)
        assert estimator.options.experimental == {"foo": "bar", "baz": 123}

    def test_experimental_options_from_instance(self) -> None:
        """Test constructing with an EstimatorOptions instance with experimental options."""
        opts = EstimatorOptions(experimental={"custom_key": "custom_value"})
        estimator = Estimator(mode=FakeBrisbane(), options=opts)
        assert estimator.options.experimental == {"custom_key": "custom_value"}

    def test_experimental_options_setter(self) -> None:
        """Test setting experimental options via the setter."""
        estimator = Estimator(mode=FakeBrisbane())
        estimator.options = {"experimental": {"test": "value"}}  # type: ignore[assignment]
        assert estimator.options.experimental == {"test": "value"}

    def test_validation_on_mutation(self) -> None:
        """Test validation errors are raised on mutation, not just construction."""
        options = ExecutionOptions(init_qubits=False)
        with pytest.raises(ValidationError):
            options.init_qubits = [0, 1]  # type: ignore[assignment]

    def test_extra_variables_are_forbidden(self) -> None:
        """Test that we can not set variables undefined by the model."""
        options = ExecutionOptions()
        with pytest.raises(ValidationError):
            options.not_a_variable = 0  # type: ignore[attr-defined]
