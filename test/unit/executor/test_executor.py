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

from ddt import data, ddt
from pydantic import ValidationError
from qiskit.circuit import QuantumCircuit

from qiskit_ibm_runtime.batch import Batch
from qiskit_ibm_runtime.executor import Executor
from qiskit_ibm_runtime.options_models.environment import EnvironmentOptions
from qiskit_ibm_runtime.options_models.execution import ExecutionOptions
from qiskit_ibm_runtime.options_models.executor import ExecutorOptions
from qiskit_ibm_runtime.qiskit_runtime_service import QiskitRuntimeService
from qiskit_ibm_runtime.quantum_program import QuantumProgram
from qiskit_ibm_runtime.session import Session

from ...decorators import mock_responses
from ...ibm_test_case import IBMTestCase
from ...registries import OneInstanceDryRunRegistry
from ...utils import get_mocked_backend


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
class TestExecutor(IBMTestCase):
    """Tests the ``Executor`` class."""

    def setUp(self) -> None:
        """Test level setup."""
        super().setUp()
        self.program = QuantumProgram(10)
        self.program.append_circuit_item(circuit=QuantumCircuit(1))

    @mock_responses(OneInstanceDryRunRegistry)
    def test_run_dry_run(self, registry):
        """Executor can run in `dry-run` mode."""
        service = QiskitRuntimeService(token="my_token")
        backend = service.backend("ibm_foo")
        executor = Executor(mode=backend)
        job = executor.run(self.program, dry_run=True)
        self.assertEqual(job.backend().name, "mock_foo")

    @data("job", "session", "batch")
    @mock_responses
    def test_mode_handling(self, mode_id, registry):
        """Executor `mode` init argument should propagate to interface and through `run()`."""
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
                expected_session_id = "session-12345"
            case "batch":
                mode = Batch(backend)
                expected_mode = mode
                expected_session_id = "session-12345"

        # Public interfaces should respect `mode`.
        executor = Executor(mode=mode)
        self.assertEqual(executor.backend(), backend)
        self.assertEqual(executor.mode, expected_mode)

        # Jobs issued should belong to a session under `session` / `batch`` modes.
        job = executor.run(self.program)
        self.assertEqual(job._session_id, expected_session_id)
