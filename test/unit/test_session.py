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

"""Tests for Session classession."""

import sys
import time
from concurrent.futures import ThreadPoolExecutor, wait

from unittest.mock import MagicMock, Mock, patch

from qiskit_ibm_runtime.fake_provider import FakeManila
from qiskit_ibm_runtime import Session
from qiskit_ibm_runtime.ibm_backend import IBMBackend
from qiskit_ibm_runtime.utils.default_session import _DEFAULT_SESSION
from .mock.fake_runtime_service import FakeRuntimeService
from ..ibm_test_case import IBMTestCase


class TestSession(IBMTestCase):
    """Class for testing the Session class."""

    def tearDown(self) -> None:
        super().tearDown()
        _DEFAULT_SESSION.set(None)

    @patch("qiskit_ibm_runtime.session.QiskitRuntimeService", autospec=True)
    def test_default_service(self, mock_service):
        """Test using default service."""
        mock_service.global_service = None
        session = Session(backend="ibm_gotham")
        self.assertIsNotNone(session.service)
        mock_service.assert_called_once()

    def test_missing_backend(self):
        """Test missing backend."""
        service = MagicMock()
        service.channel = "ibm_quantum"
        with self.assertRaises(ValueError):
            Session(service=service)

    def test_passing_ibm_backend(self):
        """Test passing in IBMBackend instance."""
        backend = MagicMock(spec=IBMBackend)
        backend._instance = None
        backend.name = "ibm_gotham"
        session = Session(service=MagicMock(), backend=backend)
        self.assertEqual(session.backend(), "ibm_gotham")

    def test_using_ibm_backend_service(self):
        """Test using service from an IBMBackend instance."""
        backend = MagicMock(spec=IBMBackend)
        backend._instance = None
        backend.name = "ibm_gotham"
        session = Session(backend=backend)
        self.assertEqual(session.service, backend.service)

    def test_max_time(self):
        """Test max time."""
        model_backend = FakeManila()
        backend = IBMBackend(
            configuration=model_backend.configuration(),
            service=MagicMock(),
            api_client=None,
        )
        max_times = [
            (42, 42),
            ("1h", 1 * 60 * 60),
            ("2h 30m 40s", 2 * 60 * 60 + 30 * 60 + 40),
            ("40s 1h", 40 + 1 * 60 * 60),
        ]
        for max_t, expected in max_times:
            with self.subTest(max_time=max_t):
                session = Session(service=MagicMock(), backend="ibm_gotham", max_time=max_t)
                self.assertEqual(session._max_time, expected)
        for max_t, expected in max_times:
            with self.subTest(max_time=max_t):
                backend.open_session(max_time=max_t)
                self.assertEqual(backend.session._max_time, expected)

    def test_run_after_close(self):
        """Test running after session is closed."""
        session = Session(service=MagicMock(), backend="ibm_gotham")
        session.cancel()
        with self.assertRaises(RuntimeError):
            session.run(program_id="program_id", inputs={})

    def test_run(self):
        """Test the run method."""
        job = MagicMock()
        job.job_id.return_value = "12345"
        service = MagicMock()
        service.run.return_value = job
        backend = "ibm_gotham"
        inputs = {"name": "bruce wayne"}
        options = {"log_level": "INFO"}
        program_id = "batman_begins"
        decoder = MagicMock()
        max_time = 42
        session = Session(service=service, backend=backend, max_time=max_time)
        session_ids = [None, job.job_id()]
        start_sessions = [True, False]

        for idx in range(2):
            session.run(
                program_id=program_id,
                inputs=inputs,
                options=options,
                result_decoder=decoder,
            )
            _, kwargs = service.run.call_args
            self.assertEqual(kwargs["program_id"], program_id)
            self.assertDictEqual(kwargs["options"], {"backend": backend, **options})
            self.assertTrue({"session_time": 42}.items() <= kwargs["options"].items())
            self.assertDictEqual(kwargs["inputs"], inputs)
            self.assertEqual(kwargs["session_id"], session_ids[idx])
            self.assertEqual(kwargs["start_session"], start_sessions[idx])
            self.assertEqual(kwargs["result_decoder"], decoder)
            self.assertEqual(session.session_id, job.job_id())
            self.assertEqual(session.backend(), backend)

    def test_run_is_thread_safe(self):
        """Test the session sends a session starter job once, and only once."""
        service = MagicMock()
        api = MagicMock()
        service._api_client = api

        def _wait_a_bit(*args, **kwargs):
            # pylint: disable=unused-argument
            switchinterval = sys.getswitchinterval()
            time.sleep(switchinterval * 2)
            return MagicMock()

        service.run = Mock(side_effect=_wait_a_bit)

        session = Session(service=service, backend="ibm_gotham")
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(map(lambda _: executor.submit(session.run, "", {}), range(5)))
            wait(results)

        calls = service.run.call_args_list
        session_starters = list(filter(lambda c: c.kwargs["start_session"] is True, calls))
        self.assertEqual(len(session_starters), 1)

    def test_close_without_run(self):
        """Test closing without run."""
        service = MagicMock()
        api = MagicMock()
        service._api_client = api
        session = Session(service=service, backend="ibm_gotham")
        session.close()
        api.close_session.assert_not_called()

    def test_context_manager(self):
        """Test session as a context manager."""
        with Session(service=MagicMock(), backend="ibm_gotham") as session:
            session.run(program_id="foo", inputs={})
            session.cancel()
        self.assertFalse(session._active)

    def test_default_backend(self):
        """Test default backend set."""
        job = MagicMock()
        job.backend().name = "ibm_gotham"
        service = MagicMock()
        service.run.return_value = job
        service.channel = "ibm_cloud"

        session = Session(service=service)
        session.run(program_id="foo", inputs={})
        self.assertEqual(session.backend(), "ibm_gotham")

    def test_global_service(self):
        """Test that global service is used in Session"""
        _ = FakeRuntimeService(channel="ibm_quantum", token="abc")
        session = Session(backend="ibmq_qasm_simulator")
        self.assertTrue(isinstance(session._service, FakeRuntimeService))
        self.assertEqual(session._service._account.token, "abc")
        _ = FakeRuntimeService(channel="ibm_quantum", token="xyz")
        session = Session(backend="ibmq_qasm_simulator")
        self.assertEqual(session._service._account.token, "xyz")
        with Session(
            service=FakeRuntimeService(channel="ibm_quantum", token="uvw"), backend="ibm_gotham"
        ) as session:
            self.assertEqual(session._service._account.token, "uvw")

    def test_session_from_id(self):
        """Create session with given session_id"""
        service = MagicMock()
        session_id = "123"
        session = Session.from_id(session_id=session_id, service=service)
        session.run(program_id="foo", inputs={})
        self.assertEqual(session.session_id, session_id)
