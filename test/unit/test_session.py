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

"""Tests for Session class."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import pytest

from qiskit_ibm_runtime import Batch, SamplerV2, Session
from qiskit_ibm_runtime.exceptions import IBMRuntimeError
from qiskit_ibm_runtime.fake_provider import FakeFractionalBackend, FakeManilaV2
from qiskit_ibm_runtime.qiskit_runtime_service import QiskitRuntimeService

from ..registries import Backend, OneInstanceDryRunRegistry
from ..registries import Session as RegistrySession

if TYPE_CHECKING:
    from ..registries import BaseRegistry


class TestSession:
    """Class for testing the Session class."""

    def test_passing_ibm_backend(self, registry: BaseRegistry) -> None:
        """Test passing in IBMBackend instance."""
        service = QiskitRuntimeService(token="my_token")
        backend = service.backend("common_backend")
        session = Session(backend=backend)
        assert session.backend() == "common_backend"

    @pytest.mark.parametrize(
        ("max_time", "expected_max_time"),
        [
            (42, 42),
            ("1h", 1 * 60 * 60),
            ("2h 30m 40s", 2 * 60 * 60 + 30 * 60 + 40),
            ("40s 1h", 40 + 1 * 60 * 60),
        ],
    )
    def test_max_time(self, max_time: int | str | None, expected_max_time: int | None) -> None:
        """Test max time."""
        backend = FakeManilaV2()

        session = Session(backend=backend, max_time=max_time)

        assert session._max_time == expected_max_time

    def test_run_after_close(self) -> None:
        """Test running after session is closed."""
        backend = FakeManilaV2()
        session = Session(backend=backend)
        session.cancel()
        with pytest.raises(IBMRuntimeError):
            session._run(program_id="program_id", inputs={})

    def test_run(self, registry: BaseRegistry) -> None:
        """Test the run method."""
        service = QiskitRuntimeService(token="my_token")
        backend = service.backend("common_backend")
        max_time = 42
        session = Session(backend=backend, max_time=max_time)
        job = session._run(program_id="foo", inputs={})
        assert job.backend().name == "common_backend"
        assert job.session_id == "session_12345"

    def test_context_manager(self, registry: BaseRegistry) -> None:
        """Test session as a context manager."""
        registry.add_session(RegistrySession("session_12345", "common_backend"), "a")
        service = QiskitRuntimeService(token="my_token")
        backend = service.backend("common_backend")
        with Session(backend=backend) as session:
            session._run(program_id="foo", inputs={})
            session.cancel()
        assert not session._active

    @pytest.mark.parametrize("calibration_id", [None, "my_id"])
    def test_session_from_id(self, calibration_id: str | None, registry: BaseRegistry) -> None:
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

    def test_correct_execution_mode(self, registry: BaseRegistry) -> None:
        """Test that the execution mode is correctly set."""
        service = QiskitRuntimeService(token="my_token")
        backend = service.backend("common_backend")
        session = Session(backend=backend)

        registry.add_session(RegistrySession(session.session_id, "common_backend"), "a")
        assert session.details()["mode"] == "dedicated"

    @pytest.mark.parametrize("session_cls", [Session, Batch])
    @pytest.mark.parametrize(
        "timestamps",
        [
            None,
            [{"status": "open", "timestamp": "2026-01-01T00:00:00Z"}],
            [
                {"status": "open", "timestamp": "2026-01-01T00:00:00Z"},
                {"status": "active", "timestamp": "2026-01-01T00:01:00Z"},
                {"status": "closed", "timestamp": "2026-01-01T00:02:00Z"},
            ],
        ],
    )
    def test_details_timestamps(
        self, session_cls: type, timestamps: list[dict] | None, registry: BaseRegistry
    ) -> None:
        """Test that the session state transitions are included in the details."""
        service = QiskitRuntimeService(token="my_token")
        backend = service.backend("common_backend")
        session = session_cls(backend=backend)

        registry.add_session(
            RegistrySession(session.session_id, "common_backend", timestamps=timestamps), "a"
        )
        # Sessions with no state transitions report an empty list of timestamps.
        assert session.details()["timestamps"] == (timestamps or [])

    def test_cm_session_fractional(self, registry: BaseRegistry) -> None:
        """Test instantiating primitive inside session context manager with fractional option."""
        registry.add_backend(Backend.from_(FakeFractionalBackend), "a")
        service = QiskitRuntimeService(token="my_token")

        backend = service.backend("fake_fractional", use_fractional_gates=True)
        with Session(backend=backend) as _:
            primitive = SamplerV2()
            assert primitive._backend.options.use_fractional_gates

    def test_backend_instance_warnings(
        self, registry: BaseRegistry, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test backend instance warnings do not appear."""
        service = QiskitRuntimeService(token="my_token")
        backend = service.backend("common_backend")
        caplog.clear()
        with caplog.at_level(logging.WARNING, logger="qiskit_ibm_runtime"):
            Session(backend=backend)
        assert not caplog.records

    @pytest.mark.registry(registry_class=OneInstanceDryRunRegistry)
    def test_run_dry_run(self, registry: BaseRegistry) -> None:
        """Session mode can run in `dry-run` mode."""
        service = QiskitRuntimeService(token="my_token")
        backend = service.backend("ibm_foo")
        with Session(backend=backend) as session:
            job = session._run(program_id="foo", inputs={}, dry_run=True)

        assert job.backend().name == "mock_foo"
