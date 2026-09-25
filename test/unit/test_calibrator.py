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

from ddt import data, ddt

from qiskit_ibm_runtime.batch import Batch
from qiskit_ibm_runtime.calibrator import Calibrator
from qiskit_ibm_runtime.options_models.calibrator import CalibratorOptions
from qiskit_ibm_runtime.options_models.environment import EnvironmentOptions
from qiskit_ibm_runtime.qiskit_runtime_service import QiskitRuntimeService
from qiskit_ibm_runtime.session import Session

from ..decorators import mock_responses
from ..ibm_test_case import IBMTestCase
from ..utils import get_mocked_backend


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


@ddt
class TestCalibrator(IBMTestCase):
    """Tests the ``Calibrator`` class."""

    @data("job", "session", "batch")
    @mock_responses
    def test_mode_handling(self, mode_id, registry):
        """Calibrator `mode` init argument should propagate to interface and through `run()`."""
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
                expected_session_id = "session_12345"
            case "batch":
                mode = Batch(backend)
                expected_mode = mode
                expected_session_id = "session_12345"

        # Public interfaces should respect `mode`.
        calibrator = Calibrator(mode=mode)
        self.assertEqual(calibrator.backend(), backend)
        self.assertEqual(calibrator.mode, expected_mode)

        # Jobs issued should belong to a session under `session` / `batch`` modes.
        job = calibrator.run()
        self.assertEqual(job._session_id, expected_session_id)
