# This code is part of Qiskit.
#
# (C) Copyright IBM 2022-2026.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Tests for Batch class."""

from qiskit_ibm_runtime import Batch
from qiskit_ibm_runtime.exceptions import IBMRuntimeError
from qiskit_ibm_runtime.fake_provider import FakeManilaV2
from qiskit_ibm_runtime.qiskit_runtime_service import QiskitRuntimeService

from ..decorators import mock_responses
from ..ibm_test_case import IBMTestCase
from ..registries import OneInstanceDryRunRegistry


class TestBatch(IBMTestCase):
    """Class for testing the Batch class."""

    @mock_responses
    def test_passing_ibm_backend(self, registry):
        """Test passing in IBMBackend instance."""
        service = QiskitRuntimeService(token="my_token")
        backend = service.backend("common_backend")
        session = Batch(backend=backend)
        self.assertEqual(session.backend(), "common_backend")

    @mock_responses
    def test_using_ibm_backend_service(self, registry):
        """Test using service from an IBMBackend instance."""
        service = QiskitRuntimeService(token="my_token")
        backend = service.backend("common_backend")
        session = Batch(backend=backend)
        self.assertEqual(session.service, backend.service)

    def test_run_after_close(self):
        """Test running after session is closed."""
        backend = FakeManilaV2()
        session = Batch(backend=backend)
        session.cancel()
        with self.assertRaises(IBMRuntimeError):
            session._run(program_id="program_id", inputs={})

    @mock_responses
    def test_context_manager(self, registry):
        """Test session as a context manager."""
        service = QiskitRuntimeService(token="my_token")
        backend = service.backend("common_backend")
        with Batch(backend=backend) as session:
            session._run(program_id="foo", inputs={})
            session.cancel()
        self.assertFalse(session._active)

    @mock_responses(OneInstanceDryRunRegistry)
    def test_run_dry_run(self, registry):
        """Batch mode can run in `dry-run` mode."""
        service = QiskitRuntimeService(token="my_token")
        backend = service.backend("ibm_foo")
        with Batch(backend=backend) as session:
            job = session._run(program_id="foo", inputs={}, dry_run=True)

        self.assertEqual(job.backend().name, "mock_foo")
