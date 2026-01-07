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
from qiskit_ibm_runtime.quantum_program import QuantumProgram

from ...ibm_test_case import IBMTestCase


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
