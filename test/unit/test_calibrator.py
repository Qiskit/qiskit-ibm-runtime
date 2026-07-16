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

"""Tests the `Calibrator` class."""

from unittest.mock import patch

from qiskit_ibm_runtime.calibrator import Calibrator
from qiskit_ibm_runtime.options_models.calibrator_options import CalibratorOptions
from qiskit_ibm_runtime.options_models.environment_options import EnvironmentOptions

from ..ibm_test_case import IBMTestCase
from ..utils import get_mocked_backend, get_mocked_session


class TestCalibratorOptions(IBMTestCase):
    """Tests option setting on the ``Calibrator`` class."""

    def test_default_options(self):
        """Test that default options are set when none are provided."""
        calibrator = Calibrator(mode=get_mocked_backend())
        self.assertIsInstance(calibrator.options, CalibratorOptions)
        self.assertEqual(calibrator.options, CalibratorOptions())

    def test_options_from_instance(self):
        """Test constructing with a CalibratorOptions instance."""
        env_opts = EnvironmentOptions(image="hi:bye")
        opts = CalibratorOptions(environment=env_opts)
        calibrator = Calibrator(mode=get_mocked_backend(), options=opts)
        self.assertIs(calibrator.options, opts)

    def test_options_from_dict(self):
        """Test constructing with a dict."""
        opts_dict = {"environment": {"image": "hi:bye"}}
        calibrator = Calibrator(mode=get_mocked_backend(), options=opts_dict)
        self.assertEqual(calibrator.options.environment.image, "hi:bye")

    def test_setter_with_instance(self):
        """Test setting options via the setter with an CalibratorOptions instance."""
        calibrator = Calibrator(mode=get_mocked_backend())
        env_opts = EnvironmentOptions(image="hi:bye")
        new_opts = CalibratorOptions(environment=env_opts)
        calibrator.options = new_opts
        self.assertIs(calibrator.options, new_opts)


class TestCalibrator(IBMTestCase):
    """Tests the ``Calibrator`` class."""

    def test_run_of_session_is_selected(self):
        """Test ``Calibrator.run`` selects the service ``run`` method, if session is specified."""
        backend_name = "ibm_hello"
        session = get_mocked_session(get_mocked_backend(backend_name))
        with (
            patch.object(session, "_run", return_value="session"),
            patch.object(session.service, "_run", return_value="service"),
        ):
            calibrator = Calibrator(mode=session)
            selected_run = calibrator.run()
            self.assertEqual(selected_run, "session")

    def test_run_of_service_is_selected(self):
        """Test ``Calibrator.run`` selects the service ``run`` method.

        This is tested when session is not specified.
        """
        backend = get_mocked_backend()
        with patch.object(backend.service, "_run", return_value="service"):
            calibrator = Calibrator(mode=backend)
            selected_run = calibrator.run()
            self.assertEqual(selected_run, "service")
