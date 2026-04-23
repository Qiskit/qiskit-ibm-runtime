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

from unittest.mock import patch

from pydantic import ValidationError

from test.utils import get_mocked_backend, get_mocked_session

from qiskit_ibm_runtime.noise_learner_v3 import NoiseLearnerV3
from qiskit_ibm_runtime.options import (
    EnvironmentOptions,
    NoiseLearnerV3Options,
    PostSelectionOptions,
    SimulatorOptions,
)
from qiskit_ibm_runtime.runtime_options import RuntimeOptions

from ...ibm_test_case import IBMTestCase


class TestNoiseLearnerV3Options(IBMTestCase):
    """Tests option setting on the ``NoiseLearnerV3`` class."""

    def test_default_options(self):
        """Test that default options are set when none are provided."""
        nlv3 = NoiseLearnerV3(mode=get_mocked_backend())
        self.assertIsInstance(nlv3.options, NoiseLearnerV3Options)
        self.assertEqual(nlv3.options, NoiseLearnerV3Options())

    def test_options_from_instance(self):
        """Test constructing with an NoiseLearnerV3Options instance."""
        opts_dict = {
            "post_selection": {"enable": True, "x_pulse_type": "rx", "strategy": "edge"},
            "environment": {"log_level": "DEBUG", "job_tags": ["tag1"]},
        }
        options = NoiseLearnerV3Options(**opts_dict)
        nlv3 = NoiseLearnerV3(mode=get_mocked_backend(), options=options)
        self.assertTrue(nlv3.options.post_selection.enable)
        self.assertEqual(nlv3.options.post_selection.x_pulse_type, "rx")
        self.assertEqual(nlv3.options.post_selection.strategy, "edge")
        self.assertEqual(nlv3.options.environment.log_level, "DEBUG")
        self.assertEqual(nlv3.options.environment.job_tags, ["tag1"])

        self.assertIsInstance(nlv3.options.environment, EnvironmentOptions)
        self.assertIsInstance(nlv3.options.simulator, SimulatorOptions)

    def test_options_from_dict(self):
        """Test constructing with a nested dict."""
        opts_dict = {
            "post_selection": {"enable": True, "x_pulse_type": "rx", "strategy": "edge"},
            "environment": {"log_level": "DEBUG", "job_tags": ["tag1"]},
        }
        nlv3 = NoiseLearnerV3(mode=get_mocked_backend(), options=opts_dict)
        self.assertTrue(nlv3.options.post_selection.enable)
        self.assertEqual(nlv3.options.post_selection.x_pulse_type, "rx")
        self.assertEqual(nlv3.options.post_selection.strategy, "edge")
        self.assertEqual(nlv3.options.environment.log_level, "DEBUG")
        self.assertEqual(nlv3.options.environment.job_tags, ["tag1"])

        self.assertIsInstance(nlv3.options.environment, EnvironmentOptions)
        self.assertIsInstance(nlv3.options.simulator, SimulatorOptions)

    def test_options_from_partial_dict(self):
        """Test constructing with a nested dict when only specifying some of the options."""
        nlv3 = NoiseLearnerV3(
            mode=get_mocked_backend(), options={"post_selection": {"strategy": "edge"}}
        )
        self.assertFalse(nlv3.options.post_selection.enable)
        self.assertEqual(nlv3.options.post_selection.x_pulse_type, "xslow")
        self.assertEqual(nlv3.options.post_selection.strategy, "edge")
        self.assertEqual(nlv3.options.environment, EnvironmentOptions())

        self.assertIsInstance(nlv3.options.environment, EnvironmentOptions)
        self.assertIsInstance(nlv3.options.simulator, SimulatorOptions)

    def test_options_constructor_invalid_type(self):
        """Test that an invalid options type raises TypeError."""
        with self.assertRaisesRegex(TypeError, "Expected NoiseLearnerV3Options or dict"):
            NoiseLearnerV3(mode=get_mocked_backend(), options="invalid")

    def test_setter_with_instance(self):
        """Test setting options via the setter with an NoiseLearnerV3Options instance."""
        nlv3 = NoiseLearnerV3(mode=get_mocked_backend())
        new_opts = NoiseLearnerV3Options(post_selection=PostSelectionOptions(strategy="edge"))
        nlv3.options = new_opts
        self.assertIs(nlv3.options, new_opts)

    def test_setter_with_dict(self):
        """Test setting options via the setter with a dict."""
        nlv3 = NoiseLearnerV3(mode=get_mocked_backend())
        nlv3.options = {"post_selection": {"strategy": "edge"}}
        self.assertIsInstance(nlv3.options, NoiseLearnerV3Options)
        self.assertEqual(nlv3.options.post_selection.strategy, "edge")

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
        nlv3.options = {"post_selection": {"strategy": "edge"}}
        # environment should be back to defaults since we replaced, not updated
        self.assertEqual(nlv3.options.environment.log_level, "WARNING")
        self.assertEqual(nlv3.options.post_selection.strategy, "edge")

    def test_experimental_options_default_empty(self):
        """Test that experimental options default to empty dict."""
        nlv3 = NoiseLearnerV3(mode=get_mocked_backend())
        self.assertEqual(nlv3.options.experimental, {})

    def test_experimental_options_from_dict(self):
        """Test constructing with experimental options in dict."""
        opts_dict = {"experimental": {"foo": "bar", "baz": 123}}
        nlv3 = NoiseLearnerV3(mode=get_mocked_backend(), options=opts_dict)
        self.assertEqual(nlv3.options.experimental, opts_dict["experimental"])

    def test_experimental_options_from_instance(self):
        """Test constructing with an NoiseLearnerV3Options instance with experimental options."""
        opts_dict = {"experimental": {"foo": "bar", "baz": 123}}
        opts = NoiseLearnerV3Options(**opts_dict)
        nlv3 = NoiseLearnerV3(mode=get_mocked_backend(), options=opts)
        self.assertEqual(nlv3.options.experimental, opts_dict["experimental"])

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


class TestNoiseLearnerV3(IBMTestCase):
    """Tests the ``NoiseLearnerV3`` class."""

    def test_run_of_session_is_selected(self):
        """Test ``.run`` selects the session ``run`` method, if session specified."""
        backend_name = "ibm_hello"
        session = get_mocked_session(get_mocked_backend(backend_name))
        with (
            patch.object(session, "_run", return_value="session"),
            patch.object(session.service, "_run", return_value="service"),
        ):
            noise_learner = NoiseLearnerV3(mode=session)
            selected_run = noise_learner.run([])
            self.assertEqual(selected_run, "session")

    def test_run_of_service_is_selected(self):
        """Test ``.run`` selects the session ``run`` method, if session not specified."""
        backend = get_mocked_backend()
        with patch.object(backend.service, "_run", return_value="service"):
            noise_learner = NoiseLearnerV3(mode=backend)
            selected_run = noise_learner.run([])
            self.assertEqual(selected_run, "service")

    def test_runtime_options(self):
        """Test the ``_runtime_options`` method."""
        learner = NoiseLearnerV3(mode=(backend := get_mocked_backend()))
        learner.options.experimental = {"image": (my_image := "my_image")}
        learner.options.max_execution_time = (max_execution_time := 3)
        learner.options.environment.job_tags = (job_tags := ["my", "tags"])
        learner.options.environment.private = (private := True)

        runtime_options = learner._runtime_options()
        self.assertIsInstance(runtime_options, RuntimeOptions)
        self.assertEqual(runtime_options.backend, backend.name)
        self.assertEqual(runtime_options.image, my_image)
        self.assertEqual(runtime_options.job_tags, job_tags)
        self.assertEqual(runtime_options.private, private)
        self.assertEqual(runtime_options.max_execution_time, max_execution_time)
