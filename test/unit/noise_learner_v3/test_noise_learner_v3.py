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

"""Tests the `NoiseLearnerV3` class."""

from ddt import data, ddt
from pydantic import ValidationError

from qiskit_ibm_runtime.batch import Batch
from qiskit_ibm_runtime.noise_learner_v3 import NoiseLearnerV3
from qiskit_ibm_runtime.options_models import (
    EnvironmentOptions,
    ExecutionOptions,
    NoiseLearnerV3Options,
)
from qiskit_ibm_runtime.qiskit_runtime_service import QiskitRuntimeService
from qiskit_ibm_runtime.session import Session

from ...decorators import mock_responses
from ...ibm_test_case import IBMTestCase
from ...registries import OneInstanceDryRunRegistry
from ...utils import get_mocked_backend


class TestNoiseLearnerV3Options(IBMTestCase):
    """Tests option setting on the ``NoiseLearnerV3`` class."""

    def test_default_options(self):
        """Test that default options are set when none are provided."""
        nlv3 = NoiseLearnerV3(mode=get_mocked_backend())
        assert isinstance(nlv3.options, NoiseLearnerV3Options)
        assert nlv3.options == NoiseLearnerV3Options()

    def test_options_from_instance(self):
        """Test constructing with an NoiseLearnerV3Options instance."""
        opts_dict = {
            "bit_flip_checks": {
                "pre_circuit": {"enable": True, "x_pulse_type": "rx", "strategy": "edge"}
            },
            "environment": {"log_level": "DEBUG", "job_tags": ["tag1"], "image": "my:image"},
            "execution": {"rep_delay": 42},
        }
        options = NoiseLearnerV3Options(**opts_dict)
        nlv3 = NoiseLearnerV3(mode=get_mocked_backend(), options=options)
        assert nlv3.options.bit_flip_checks.pre_circuit.enable
        assert nlv3.options.bit_flip_checks.pre_circuit.x_pulse_type == "rx"
        assert nlv3.options.bit_flip_checks.pre_circuit.strategy == "edge"
        assert nlv3.options.environment.log_level == "DEBUG"
        assert nlv3.options.environment.job_tags == ["tag1"]
        assert nlv3.options.environment.image == "my:image"
        assert nlv3.options.execution.rep_delay == 42

        assert isinstance(nlv3.options.environment, EnvironmentOptions)
        assert isinstance(nlv3.options.execution, ExecutionOptions)

    def test_options_from_dict(self):
        """Test constructing with a nested dict."""
        opts_dict = {
            "bit_flip_checks": {
                "pre_circuit": {"enable": True, "x_pulse_type": "rx", "strategy": "edge"}
            },
            "environment": {"log_level": "DEBUG", "job_tags": ["tag1"], "image": "my:image"},
            "execution": {"rep_delay": 42},
        }
        nlv3 = NoiseLearnerV3(mode=get_mocked_backend(), options=opts_dict)
        assert nlv3.options.bit_flip_checks.pre_circuit.enable
        assert nlv3.options.bit_flip_checks.pre_circuit.x_pulse_type == "rx"
        assert nlv3.options.bit_flip_checks.pre_circuit.strategy == "edge"
        assert nlv3.options.environment.log_level == "DEBUG"
        assert nlv3.options.environment.job_tags == ["tag1"]
        assert nlv3.options.environment.image == "my:image"
        assert nlv3.options.execution.rep_delay == 42

        assert isinstance(nlv3.options.environment, EnvironmentOptions)
        assert isinstance(nlv3.options.execution, ExecutionOptions)

    def test_options_from_partial_dict(self):
        """Test constructing with a nested dict when only specifying some of the options."""
        nlv3 = NoiseLearnerV3(
            mode=get_mocked_backend(),
            options={"bit_flip_checks": {"pre_circuit": {"strategy": "edge"}}},
        )
        assert not nlv3.options.bit_flip_checks.pre_circuit.enable
        assert nlv3.options.bit_flip_checks.pre_circuit.x_pulse_type == "xslow"
        assert nlv3.options.bit_flip_checks.pre_circuit.strategy == "edge"
        assert nlv3.options.environment == EnvironmentOptions()
        assert nlv3.options.execution == ExecutionOptions()

        assert isinstance(nlv3.options.environment, EnvironmentOptions)
        assert isinstance(nlv3.options.execution, ExecutionOptions)

    def test_options_constructor_invalid_type(self):
        """Test that an invalid options type raises TypeError."""
        with self.assertRaisesRegex(TypeError, "Expected NoiseLearnerV3Options or dict"):
            NoiseLearnerV3(mode=get_mocked_backend(), options="invalid")

    def test_setter_with_dict(self):
        """Test setting options via the setter with a dict."""
        nlv3 = NoiseLearnerV3(mode=get_mocked_backend())
        nlv3.options = {"layer_pair_depths": [1, 2]}
        assert isinstance(nlv3.options, NoiseLearnerV3Options)
        assert nlv3.options.layer_pair_depths == [1, 2]

    def test_setter_invalid_type(self):
        """Test that setting options with an invalid type raises TypeError."""
        nlv3 = NoiseLearnerV3(mode=get_mocked_backend())
        with self.assertRaisesRegex(TypeError, "Expected NoiseLearnerV3Options or dict"):
            nlv3.options = 42

    def test_setter_replaces_options(self):
        """Test that the setter replaces (not updates) the options."""
        nlv3 = NoiseLearnerV3(
            mode=get_mocked_backend(), options={"environment": {"log_level": "DEBUG"}}
        )
        nlv3.options = {"layer_pair_depths": [1, 2]}
        # environment should be back to defaults since we replaced, not updated
        assert nlv3.options.environment.log_level == "WARNING"
        assert nlv3.options.layer_pair_depths == [1, 2]

    def test_experimental_options_default_empty(self):
        """Test that experimental options default to empty dict."""
        nlv3 = NoiseLearnerV3(mode=get_mocked_backend())
        assert nlv3.options.experimental == {}

    def test_experimental_options_from_dict(self):
        """Test constructing with experimental options in dict."""
        opts_dict = {"experimental": {"foo": "bar", "baz": 123}}
        nlv3 = NoiseLearnerV3(mode=get_mocked_backend(), options=opts_dict)
        assert nlv3.options.experimental == opts_dict["experimental"]

    def test_experimental_options_from_instance(self):
        """Test constructing with an NoiseLearnerV3Options instance with experimental options."""
        opts_dict = {"experimental": {"foo": "bar", "baz": 123}}
        opts = NoiseLearnerV3Options(**opts_dict)
        nlv3 = NoiseLearnerV3(mode=get_mocked_backend(), options=opts)
        assert nlv3.options.experimental == opts_dict["experimental"]

    def test_validation_on_mutation(self):
        """Test validation errors are raised on mutation, not just construction."""
        options = NoiseLearnerV3Options()
        with self.assertRaises(ValidationError):
            options.num_randomizations = "invalid"

    def test_extra_variables_are_forbidden(self):
        """Test that we can not set variables undefined by the model."""
        options = NoiseLearnerV3Options()
        with self.assertRaises(ValidationError):
            options.not_a_variable = 0


@ddt
class TestNoiseLearnerV3(IBMTestCase):
    """Tests the ``NoiseLearnerV3`` class."""

    @mock_responses(OneInstanceDryRunRegistry)
    def test_run_dry_run(self, registry):
        """NoiseLearnerV3 can run in `dry-run` mode."""
        service = QiskitRuntimeService(token="my_token")
        backend = service.backend("ibm_foo")
        noise_learner = NoiseLearnerV3(mode=backend)
        job = noise_learner.run([], dry_run=True)
        assert job.backend().name == "mock_foo"

    @data("job", "session", "batch")
    @mock_responses
    def test_mode_handling(self, mode_id, registry):
        """NoiseLearner `mode` init argument should propagate to interface and through `run()`."""
        service = QiskitRuntimeService(token="my_token")
        backend = service.backend("common_backend")

        match mode_id:
            case "job":
                mode = backend
                expected_mode = None
                expected_session_id = None
            case "session":
                mode = Session(backend)
                expected_mode = mode
                expected_session_id = "session_12345"
            case "batch":
                mode = Batch(backend)
                expected_mode = mode
                expected_session_id = "session_12345"

        # Public interfaces should respect `mode`.
        noise_learner = NoiseLearnerV3(mode=mode)
        assert noise_learner.backend() == backend
        assert noise_learner.mode == expected_mode

        # Jobs issued should belong to a session under `session` / `batch`` modes.
        job = noise_learner.run([])
        assert job._session_id == expected_session_id
