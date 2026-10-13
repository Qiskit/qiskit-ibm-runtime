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

"""Tests for Session classession."""

from ddt import data, ddt, unpack

from qiskit_ibm_runtime import Batch, SamplerV2, Session
from qiskit_ibm_runtime.exceptions import IBMRuntimeError
from qiskit_ibm_runtime.fake_provider import FakeFractionalBackend, FakeManilaV2
from qiskit_ibm_runtime.qiskit_runtime_service import QiskitRuntimeService

from ..decorators import mock_responses
from ..ibm_test_case import IBMTestCase
from ..registries import Backend, OneInstanceDryRunRegistry
from ..registries import Session as RegistrySession
from ..utils import combine


@ddt
class TestSession(IBMTestCase):
    """Class for testing the Session class."""

    @mock_responses
    def test_passing_ibm_backend(self, registry):
        """Test passing in IBMBackend instance."""
        service = QiskitRuntimeService(token="my_token")
        backend = service.backend("common_backend")
        session = Session(backend=backend)
        assert session.backend() == "common_backend"

    @data(
        (42, 42),
        ("1h", 1 * 60 * 60),
        ("2h 30m 40s", 2 * 60 * 60 + 30 * 60 + 40),
        ("40s 1h", 40 + 1 * 60 * 60),
    )
    @unpack
    def test_max_time(self, max_time, expected_max_time):
        """Test max time."""
        backend = FakeManilaV2()

        session = Session(backend=backend, max_time=max_time)

        assert session._max_time == expected_max_time

    def test_run_after_close(self):
        """Test running after session is closed."""
        backend = FakeManilaV2()
        session = Session(backend=backend)
        session.cancel()
        with self.assertRaises(IBMRuntimeError):
            session._run(program_id="program_id", inputs={})

    @mock_responses
    def test_run(self, registry):
        """Test the run method."""
        service = QiskitRuntimeService(token="my_token")
        backend = service.backend("common_backend")
        max_time = 42
        session = Session(backend=backend, max_time=max_time)
        job = session._run(program_id="foo", inputs={})
        assert job.backend().name == "common_backend"
        assert job.session_id == "session_12345"

    @mock_responses
    def test_context_manager(self, registry):
        """Test session as a context manager."""
        registry.add_session(RegistrySession("session_12345", "common_backend"), "a")
        service = QiskitRuntimeService(token="my_token")
        backend = service.backend("common_backend")
        with Session(backend=backend) as session:
            session._run(program_id="foo", inputs={})
            session.cancel()
        assert not session._active

    @data(None, "my_id")
    @mock_responses
    def test_session_from_id(self, calibration_id, registry):
        """Create session with given session_id."""
        session_id = "123"
        registry.add_session(RegistrySession(session_id, "common_backend"), "a")
        if calibration_id:
            registry.backends["a"]["common_backend"].calibrations[calibration_id] = {}
        service = QiskitRuntimeService(token="my_token")

        session = Session.from_id(
            session_id=session_id, service=service, calibration_id=calibration_id
        )
        session._run(program_id="foo", inputs={})
        assert session.session_id == session_id

    @mock_responses
    def test_correct_execution_mode(self, registry):
        """Test that the execution mode is correctly set."""
        service = QiskitRuntimeService(token="my_token")
        backend = service.backend("common_backend")
        session = Session(backend=backend)

        registry.add_session(RegistrySession(session.session_id, "common_backend"), "a")
        assert session.details()["mode"] == "dedicated"

    @combine(
        session_cls=[Session, Batch],
        timestamps=[
            None,
            [{"status": "open", "timestamp": "2026-01-01T00:00:00Z"}],
            [
                {"status": "open", "timestamp": "2026-01-01T00:00:00Z"},
                {"status": "active", "timestamp": "2026-01-01T00:01:00Z"},
                {"status": "closed", "timestamp": "2026-01-01T00:02:00Z"},
            ],
        ],
    )
    @mock_responses
    def test_details_timestamps(self, session_cls, timestamps, registry):
        """Test that the session state transitions are included in the details."""
        service = QiskitRuntimeService(token="my_token")
        backend = service.backend("common_backend")
        session = session_cls(backend=backend)

        registry.add_session(
            RegistrySession(session.session_id, "common_backend", timestamps=timestamps), "a"
        )
        # Sessions with no state transitions report an empty list of timestamps.
        assert session.details()["timestamps"] == (timestamps or [])

    @mock_responses
    def test_cm_session_fractional(self, registry):
        """Test instantiating primitive inside session context manager with fractional option."""
        registry.add_backend(Backend.from_(FakeFractionalBackend), "a")
        service = QiskitRuntimeService(token="my_token")

        backend = service.backend("fake_fractional", use_fractional_gates=True)
        with Session(backend=backend) as _:
            primitive = SamplerV2()
            assert primitive._backend.options.use_fractional_gates

    @mock_responses
    def test_backend_instance_warnings(self, registry):
        """Test backend instance warnings do not appear."""
        service = QiskitRuntimeService(token="my_token")
        backend = service.backend("common_backend")
        with self.assertNoLogs("qiskit_ibm_runtime", level="WARNING"):
            Session(backend=backend)

    @mock_responses(OneInstanceDryRunRegistry)
    def test_run_dry_run(self, registry):
        """Session mode can run in `dry-run` mode."""
        service = QiskitRuntimeService(token="my_token")
        backend = service.backend("ibm_foo")
        with Session(backend=backend) as session:
            job = session._run(program_id="foo", inputs={}, dry_run=True)

        assert job.backend().name == "mock_foo"
