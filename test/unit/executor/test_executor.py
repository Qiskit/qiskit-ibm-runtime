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

"""Tests the `Executor` class."""

from unittest.mock import patch

from test.utils import get_mocked_backend, get_mocked_session

from qiskit_ibm_runtime.executor import Executor
from qiskit_ibm_runtime.options.executor_options import (
    ExecutorOptions,
    ExecutionOptions,
    EnvironmentOptions,
)
from qiskit_ibm_runtime.quantum_program import QuantumProgram

from ...ibm_test_case import IBMTestCase


class TestExecutorOptions(IBMTestCase):
    """Tests option setting on the ``Executor`` class."""

    def test_default_options(self):
        """Test that default options are set when none are provided."""
        executor = Executor(mode=get_mocked_backend())
        self.assertIsInstance(executor.options, ExecutorOptions)
        self.assertEqual(executor.options, ExecutorOptions())

    def test_options_from_instance(self):
        """Test constructing with an ExecutorOptions instance."""
        opts = ExecutorOptions(execution=ExecutionOptions(init_qubits=False))
        executor = Executor(mode=get_mocked_backend(), options=opts)
        self.assertIs(executor.options, opts)
        self.assertFalse(executor.options.execution.init_qubits)

    def test_options_from_dict(self):
        """Test constructing with a nested dict."""
        opts_dict = {
            "execution": {"init_qubits": False, "rep_delay": 0.5},
            "environment": {"log_level": "DEBUG", "job_tags": ["tag1"]},
        }
        executor = Executor(mode=get_mocked_backend(), options=opts_dict)
        self.assertFalse(executor.options.execution.init_qubits)
        self.assertEqual(executor.options.execution.rep_delay, 0.5)
        self.assertEqual(executor.options.environment.log_level, "DEBUG")
        self.assertEqual(executor.options.environment.job_tags, ["tag1"])

    def test_options_from_partial_dict(self):
        """Test constructing with a nested dict when only specifying some of the options."""
        executor = Executor(
            mode=get_mocked_backend(), options={"execution": {"init_qubits": False}}
        )
        self.assertFalse(executor.options.execution.init_qubits)
        self.assertIsNone(executor.options.execution.rep_delay)
        self.assertEqual(executor.options.environment, EnvironmentOptions())

    def test_options_constructor_invalid_type(self):
        """Test that an invalid options type raises TypeError."""
        with self.assertRaisesRegex(TypeError, "Expected ExecutorOptions or dict"):
            Executor(mode=get_mocked_backend(), options="invalid")

    def test_setter_with_instance(self):
        """Test setting options via the setter with an ExecutorOptions instance."""
        executor = Executor(mode=get_mocked_backend())
        new_opts = ExecutorOptions(execution=ExecutionOptions(init_qubits=False))
        executor.options = new_opts
        self.assertIs(executor.options, new_opts)

    def test_setter_with_dict(self):
        """Test setting options via the setter with a dict."""
        executor = Executor(mode=get_mocked_backend())
        executor.options = {"execution": {"init_qubits": False}}
        self.assertIsInstance(executor.options, ExecutorOptions)
        self.assertFalse(executor.options.execution.init_qubits)

    def test_setter_invalid_type(self):
        """Test that setting options with an invalid type raises TypeError."""
        executor = Executor(mode=get_mocked_backend())
        with self.assertRaisesRegex(TypeError, "Expected ExecutorOptions or dict"):
            executor.options = 42

    def test_setter_replaces_options(self):
        """Test that the setter replaces (not updates) the options."""
        executor = Executor(
            mode=get_mocked_backend(), options={"environment": {"log_level": "DEBUG"}}
        )
        executor.options = {"execution": {"init_qubits": False}}
        # environment should be back to defaults since we replaced, not updated
        self.assertEqual(executor.options.environment.log_level, "WARNING")
        self.assertFalse(executor.options.execution.init_qubits)

    def test_experimental_options_default_empty(self):
        """Test that experimental options default to empty dict."""
        executor = Executor(mode=get_mocked_backend())
        self.assertEqual(executor.options.experimental, {})

    def test_experimental_options_from_dict(self):
        """Test constructing with experimental options in dict."""
        opts_dict = {"experimental": {"foo": "bar", "baz": 123}}
        executor = Executor(mode=get_mocked_backend(), options=opts_dict)
        self.assertEqual(executor.options.experimental, {"foo": "bar", "baz": 123})

    def test_experimental_options_from_instance(self):
        """Test constructing with an ExecutorOptions instance with experimental options."""
        opts = ExecutorOptions(experimental={"custom_key": "custom_value"})
        executor = Executor(mode=get_mocked_backend(), options=opts)
        self.assertEqual(executor.options.experimental, {"custom_key": "custom_value"})

    def test_experimental_options_setter(self):
        """Test setting experimental options via the setter."""
        executor = Executor(mode=get_mocked_backend())
        executor.options = {"experimental": {"test": "value"}}
        self.assertEqual(executor.options.experimental, {"test": "value"})


class TestExecutor(IBMTestCase):
    """Tests the ``Executor`` class."""

    def test_run_of_session_is_selected(self):
        """Test that ``Executor.run`` selects the ``run`` method
        of the session, if a session is specified."""
        backend_name = "ibm_hello"
        session = get_mocked_session(get_mocked_backend(backend_name))
        with (
            patch.object(session, "_run", return_value="session"),
            patch.object(session.service, "_run", return_value="service"),
        ):
            executor = Executor(mode=session)
            selected_run = executor.run(QuantumProgram(10))
            self.assertEqual(selected_run, "session")

    def test_run_of_service_is_selected(self):
        """Test that ``Executor.run`` selects the ``run`` method
        of the service, if a session is not specified."""
        backend = get_mocked_backend()
        with patch.object(backend.service, "_run", return_value="service"):
            executor = Executor(mode=backend)
            selected_run = executor.run(QuantumProgram(10))
            self.assertEqual(selected_run, "service")
