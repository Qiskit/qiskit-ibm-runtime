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
from unittest.mock import MagicMock

from qiskit_ibm_runtime.fake_provider import FakeManilaV2
from qiskit_ibm_runtime import Session, SamplerV2
from qiskit_ibm_runtime.ibm_backend import IBMBackend
from qiskit_ibm_runtime.exceptions import IBMRuntimeError
from qiskit_ibm_runtime.utils.default_session import _DEFAULT_SESSION

from .mock.fake_runtime_service import FakeRuntimeService
from .mock.fake_api_backend import FakeApiBackendSpecs
from ..ibm_test_case import IBMTestCase
from ..utils import get_mocked_backend


class TestSession(IBMTestCase):
    """Class for testing the Session class."""

    def tearDown(self) -> None:
        super().tearDown()
        _DEFAULT_SESSION.set(None)

    def test_passing_ibm_backend(self):
        """Test passing in IBMBackend instance."""
        backend_name = "ibm_gotham"
        backend = get_mocked_backend(name=backend_name)
        session = Session(backend=backend)
        self.assertEqual(session.backend(), backend_name)

    def test_max_time(self):
        """Test max time."""
        model_backend = FakeManilaV2()
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
                backend = get_mocked_backend("ibm_gotham")
                session = Session(backend=backend, max_time=max_t)
                self.assertEqual(session._max_time, expected)

    def test_run_after_close(self):
        """Test running after session is closed."""
        backend = get_mocked_backend("ibm_gotham")
        session = Session(backend=backend)
        session.cancel()
        with self.assertRaises(IBMRuntimeError):
            session._run(program_id="program_id", inputs={})

    def test_run(self):
        """Test the run method."""
        backend_name = "ibm_gotham"
        backend = get_mocked_backend(backend_name)
        job = MagicMock()
        job.job_id.return_value = "12345"
        service = backend.service
        service._run.return_value = job
        inputs = {"name": "bruce wayne"}
        options = {"log_level": "INFO"}
        program_id = "batman_begins"
        decoder = MagicMock()
        max_time = 42
        session = Session(backend=backend, max_time=max_time)

        session._run(
            program_id=program_id,
            inputs=inputs,
            options=options,
            result_decoder=decoder,
        )
        _, kwargs = service._run.call_args
        self.assertEqual(kwargs["program_id"], program_id)
        self.assertDictEqual(kwargs["options"], {"backend": backend, **options})
        self.assertDictEqual(kwargs["inputs"], inputs)
        self.assertEqual(kwargs["result_decoder"], decoder)
        self.assertEqual(session.backend(), backend_name)

    def test_context_manager(self):
        """Test session as a context manager."""
        backend = get_mocked_backend("ibm_gotham")
        with Session(backend=backend) as session:
            session._run(program_id="foo", inputs={})
            session.cancel()
        self.assertFalse(session._active)

    def test_session_from_id(self):
        """Create session with given session_id"""
        service = FakeRuntimeService(channel="ibm_quantum_platform", token="abc")
        session_id = "123"
        session = Session.from_id(session_id=session_id, service=service)
        session._run(program_id="foo", inputs={})
        session._create_session = MagicMock()
        self.assertTrue(session._create_session.assert_not_called)
        self.assertEqual(session.session_id, session_id)

    def test_correct_execution_mode(self):
        """Test that the execution mode is correctly set."""
        _ = FakeRuntimeService(channel="ibm_quantum_platform", token="abc")
        backend = get_mocked_backend("ibm_gotham")
        session = Session(backend=backend)
        self.assertEqual(session.details()["mode"], "dedicated")

    def test_cm_session_fractional(self):
        """Test instantiating primitive inside session context manager with the fractional optin."""
        service = FakeRuntimeService(
            channel="ibm_quantum_platform",
            token="abc",
            backend_specs=[FakeApiBackendSpecs(backend_name="FakeFractionalBackend")],
        )
        backend = service.backend("fake_fractional", use_fractional_gates=True)
        with Session(backend=backend) as _:
            primitive = SamplerV2()
            self.assertTrue(primitive._backend.options.use_fractional_gates)

    def test_backend_instance_warnings(self):
        """Test backend instance warnings do not appear."""
        if sys.version_info < (3, 10):
            self.skipTest("assertNoLogs is not supported")
        backend_name = "ibm_gotham"
        backend = get_mocked_backend(name=backend_name)
        with self.assertNoLogs("qiskit_ibm_runtime", level="WARNING"):
            Session(backend=backend)
