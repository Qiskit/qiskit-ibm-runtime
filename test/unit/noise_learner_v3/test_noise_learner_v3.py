# This code is part of Qiskit.
#
# (C) Copyright IBM 2025.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Tests the `NoiseLearnerV3` class."""

from test.utils import get_mocked_backend, get_mocked_session

from qiskit_ibm_runtime import Session
from qiskit_ibm_runtime.noise_learner_v3 import NoiseLearnerV3

from ...ibm_test_case import IBMTestCase


class TestNoiseLearnerV3(IBMTestCase):
    """Tests the ``NoiseLearnerV3`` class."""
    def test_run_of_session_is_selected(self):
        """Test that ``NoiseLearner.run`` selects the ``run`` method
        of the session, if a session is specified."""
        backend_name = "ibm_hello"
        session = get_mocked_session(get_mocked_backend(backend_name))
        session.service.reset_mock()
        noise_learner = NoiseLearnerV3(mode=session)
        session._run.return_value = "session"
        session.service._run = lambda *args, **kwargs: "service"
        selected_run = noise_learner.run([])
        self.assertEqual(selected_run, "session")

    def test_run_of_service_is_selected(self):
        """Test that ``NoiseLearner.run`` selects the ``run`` method
        of the service, if a session is not specified."""
        backend = get_mocked_backend()
        service = backend.service
        noise_learner = NoiseLearnerV3(mode=backend)
        service._run.return_value = "service"
        selected_run = noise_learner.run([])
        self.assertEqual(selected_run, "service")
