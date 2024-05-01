# This code is part of Qiskit.
#
# (C) Copyright IBM 2022.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Tests for Batch class."""

from unittest.mock import MagicMock

from qiskit_ibm_runtime import Batch
from qiskit_ibm_runtime.utils.default_session import _DEFAULT_SESSION
from qiskit_ibm_runtime.exceptions import IBMRuntimeError

from ..ibm_test_case import IBMTestCase
from ..utils import get_mocked_backend


class TestBatch(IBMTestCase):
    """Class for testing the Batch class."""

    def tearDown(self) -> None:
        super().tearDown()
        _DEFAULT_SESSION.set(None)

    def test_passing_ibm_backend(self):
        """Test passing in IBMBackend instance."""
        name = "ibm_gotham"
        backend = get_mocked_backend(name=name)
        session = Batch(service=MagicMock(), backend=backend)
        self.assertEqual(session.backend(), name)

    def test_using_ibm_backend_service(self):
        """Test using service from an IBMBackend instance."""
        name = "ibm_gotham"
        backend = get_mocked_backend(name=name)
        session = Batch(backend=backend)
        self.assertEqual(session.service, backend.service)

    def test_run_after_close(self):
        """Test running after session is closed."""
        session = Batch(service=MagicMock(), backend="ibm_gotham")
        session.cancel()
        with self.assertRaises(IBMRuntimeError):
            session.run(program_id="program_id", inputs={})

    def test_context_manager(self):
        """Test session as a context manager."""
        with Batch(service=MagicMock(), backend="ibm_gotham") as session:
            session.run(program_id="foo", inputs={})
            session.cancel()
        self.assertFalse(session._active)
