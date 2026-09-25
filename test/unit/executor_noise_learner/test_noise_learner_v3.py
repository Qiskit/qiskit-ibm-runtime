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

from ddt import data, ddt
from pydantic import ValidationError
from qiskit import QuantumCircuit

from qiskit_ibm_runtime.batch import Batch
from qiskit_ibm_runtime.executor_noise_learner.noise_learner_v3 import NoiseLearnerV3
from qiskit_ibm_runtime.fake_provider import FakeBrisbane
from qiskit_ibm_runtime.options_models.environment import EnvironmentOptions
from qiskit_ibm_runtime.options_models.execution import ExecutionOptions
from qiskit_ibm_runtime.options_models.noise_learner_v3 import NoiseLearnerV3Options
from qiskit_ibm_runtime.qiskit_runtime_service import QiskitRuntimeService
from qiskit_ibm_runtime.session import Session

from ...decorators import mock_responses
from ...ibm_test_case import IBMTestCase
from ...registries import OneInstanceDryRunRegistry


class TestNoiseLearnerUsingOptions(IBMTestCase):
    """Tests option setting on the ``NoiseLearnerV3`` class."""

    def test_default_options(self):
        """Test that default options are set when none are provided."""
        noise_learner = NoiseLearnerV3(mode=FakeBrisbane())
        self.assertIsInstance(noise_learner.options, NoiseLearnerV3Options)
        self.assertEqual(noise_learner.options, NoiseLearnerV3Options())

    def test_options_from_instance(self):
        """Test constructing with an NoiseLearnerV3Options instance."""
        opts = NoiseLearnerV3Options(execution=ExecutionOptions(init_qubits=False))
        noise_learner = NoiseLearnerV3(mode=FakeBrisbane(), options=opts)
        self.assertIs(noise_learner.options, opts)
        self.assertFalse(noise_learner.options.execution.init_qubits)

    def test_options_from_dict(self):
        """Test constructing with a nested dict."""
        opts_dict = {
            "execution": {"init_qubits": False, "rep_delay": 0.5},
            "environment": {"log_level": "DEBUG", "job_tags": ["tag1"]},
        }
        noise_learner = NoiseLearnerV3(mode=FakeBrisbane(), options=opts_dict)
        self.assertFalse(noise_learner.options.execution.init_qubits)
        self.assertEqual(noise_learner.options.execution.rep_delay, 0.5)
        self.assertEqual(noise_learner.options.environment.log_level, "DEBUG")
        self.assertEqual(noise_learner.options.environment.job_tags, ["tag1"])

    def test_options_from_partial_dict(self):
        """Test constructing with a nested dict when only specifying some of the options."""
        noise_learner = NoiseLearnerV3(
            mode=FakeBrisbane(), options={"execution": {"init_qubits": False}}
        )
        self.assertFalse(noise_learner.options.execution.init_qubits)
        self.assertIsNone(noise_learner.options.execution.rep_delay)
        self.assertEqual(noise_learner.options.environment, EnvironmentOptions())

    def test_options_constructor_invalid_type(self):
        """Test that an invalid options type raises TypeError."""
        with self.assertRaisesRegex(TypeError, "Expected NoiseLearnerV3Options or dict"):
            NoiseLearnerV3(mode=FakeBrisbane(), options="invalid")

    def test_setter_with_instance(self):
        """Test setting options via the setter with an NoiseLearnerV3Options instance."""
        noise_learner = NoiseLearnerV3(mode=FakeBrisbane())
        new_opts = NoiseLearnerV3Options(execution=ExecutionOptions(init_qubits=False))
        noise_learner.options = new_opts
        self.assertIs(noise_learner.options, new_opts)

    def test_setter_with_dict(self):
        """Test setting options via the setter with a dict."""
        noise_learner = NoiseLearnerV3(mode=FakeBrisbane())
        noise_learner.options = {"execution": {"init_qubits": False}}
        self.assertIsInstance(noise_learner.options, NoiseLearnerV3Options)
        self.assertFalse(noise_learner.options.execution.init_qubits)

    def test_setter_invalid_type(self):
        """Test that setting options with an invalid type raises TypeError."""
        noise_learner = NoiseLearnerV3(mode=FakeBrisbane())
        with self.assertRaisesRegex(TypeError, "Expected NoiseLearnerV3Options or dict"):
            noise_learner.options = 42

    def test_setter_replaces_options(self):
        """Test that the setter replaces (not updates) the options."""
        noise_learner = NoiseLearnerV3(
            mode=FakeBrisbane(), options={"environment": {"log_level": "DEBUG"}}
        )
        noise_learner.options = {"execution": {"init_qubits": False}}
        # environment should be back to defaults since we replaced, not updated
        self.assertEqual(noise_learner.options.environment.log_level, "WARNING")
        self.assertFalse(noise_learner.options.execution.init_qubits)

    def test_experimental_options_default_empty(self):
        """Test that experimental options default to empty dict."""
        noise_learner = NoiseLearnerV3(mode=FakeBrisbane())
        self.assertEqual(noise_learner.options.experimental, {})

    def test_experimental_options_from_dict(self):
        """Test constructing with experimental options in dict."""
        opts_dict = {"experimental": {"foo": "bar", "baz": 123}}
        noise_learner = NoiseLearnerV3(mode=FakeBrisbane(), options=opts_dict)
        self.assertEqual(noise_learner.options.experimental, {"foo": "bar", "baz": 123})

    def test_experimental_options_from_instance(self):
        """Test constructing with an NoiseLearnerV3Options instance with experimental options."""
        opts = NoiseLearnerV3Options(experimental={"custom_key": "custom_value"})
        noise_learner = NoiseLearnerV3(mode=FakeBrisbane(), options=opts)
        self.assertEqual(noise_learner.options.experimental, {"custom_key": "custom_value"})

    def test_experimental_options_setter(self):
        """Test setting experimental options via the setter."""
        noise_learner = NoiseLearnerV3(mode=FakeBrisbane())
        noise_learner.options = {"experimental": {"test": "value"}}
        self.assertEqual(noise_learner.options.experimental, {"test": "value"})

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


@ddt
class TestNoiseLearnerRun(IBMTestCase):
    """Tests for the NoiseLearnerV3.run() method."""

    @mock_responses(OneInstanceDryRunRegistry)
    def test_run_dry_run(self, registry):
        """NoiseLearnerV3 can run in `dry-run` mode."""
        service = QiskitRuntimeService(token="my_token")
        backend = service.backend("ibm_foo")
        noise_learner = NoiseLearnerV3(mode=backend)

        circuit = QuantumCircuit(2)
        circuit.h(0)
        circuit.cx(0, 1)

        job = noise_learner.run([circuit], dry_run=True)
        self.assertEqual(job.backend().name, "mock_foo")

    @data("job", "session", "batch")
    @mock_responses
    def test_mode_handling(self, mode_id, registry):
        """NoiseLearnerV3 `mode` init argument should propagate to interface and through `run()`."""
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
        self.assertEqual(noise_learner.backend(), backend)
        self.assertEqual(noise_learner.mode, expected_mode)

        # Jobs issued should belong to a session under `session` / `batch`` modes.
        circuit = QuantumCircuit(2)
        circuit.h(0)
        circuit.cx(0, 1)

        job = noise_learner.run([circuit])
        self.assertEqual(job._session_id, expected_session_id)
