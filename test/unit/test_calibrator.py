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
from pydantic import ValidationError

from qiskit_ibm_runtime.batch import Batch
from qiskit_ibm_runtime.calibrator import Calibrator
from qiskit_ibm_runtime.options_models.calibrator import CalibratorOptions, ReadoutAngleOptions
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
        assert isinstance(calibrator.options, CalibratorOptions)
        assert calibrator.options == CalibratorOptions()

    def test_options_from_instance(self):
        """Test constructing with a CalibratorOptions instance."""
        opts = CalibratorOptions(readout_angle=ReadoutAngleOptions(enable=False))
        calibrator = Calibrator(mode=get_mocked_backend(), options=opts)
        assert calibrator.options is opts
        assert not calibrator.options.readout_angle.enable

    def test_options_from_dict(self):
        """Test constructing with a nested dict."""
        opts_dict = {
            "readout_angle": {"enable": False},
            "environment": {"log_level": "DEBUG"},
        }
        calibrator = Calibrator(mode=get_mocked_backend(), options=opts_dict)
        assert not calibrator.options.readout_angle.enable
        assert calibrator.options.environment.log_level == "DEBUG"

    def test_options_from_partial_dict(self):
        """Test constructing with a nested dict when only specifying some of the options."""
        calibrator = Calibrator(
            mode=get_mocked_backend(), options={"readout_angle": {"enable": False}}
        )
        assert not calibrator.options.readout_angle.enable
        assert calibrator.options.environment == EnvironmentOptions()

    def test_options_constructor_invalid_type(self):
        """Test that an invalid options type raises TypeError."""
        with self.assertRaisesRegex(TypeError, "Expected CalibratorOptions or dict"):
            Calibrator(mode=get_mocked_backend(), options="invalid")

    def test_setter_with_instance(self):
        """Test setting options via the setter with a CalibratorOptions instance."""
        calibrator = Calibrator(mode=get_mocked_backend())
        new_opts = CalibratorOptions(readout_angle=ReadoutAngleOptions(enable=False))
        calibrator.options = new_opts
        assert calibrator.options is new_opts

    def test_setter_with_dict(self):
        """Test setting options via the setter with a dict."""
        calibrator = Calibrator(mode=get_mocked_backend())
        calibrator.options = {"readout_angle": {"enable": False}}
        assert isinstance(calibrator.options, CalibratorOptions)
        assert not calibrator.options.readout_angle.enable

    def test_setter_invalid_type(self):
        """Test that setting options with an invalid type raises TypeError."""
        calibrator = Calibrator(mode=get_mocked_backend())
        with self.assertRaisesRegex(TypeError, "Expected CalibratorOptions or dict"):
            calibrator.options = 42

    def test_setter_replaces_options(self):
        """Test that the setter replaces (not updates) the options."""
        calibrator = Calibrator(
            mode=get_mocked_backend(), options={"environment": {"log_level": "DEBUG"}}
        )
        calibrator.options = {"readout_angle": {"enable": False}}
        # environment should be back to defaults since we replaced, not updated
        assert calibrator.options.environment.log_level == "WARNING"
        assert not calibrator.options.readout_angle.enable

    def test_experimental_options_default_empty(self):
        """Test that experimental options default to empty dict."""
        calibrator = Calibrator(mode=get_mocked_backend())
        assert calibrator.options.experimental == {}

    def test_experimental_options_from_dict(self):
        """Test constructing with experimental options in dict."""
        opts_dict = {"experimental": {"foo": "bar", "baz": 123}}
        calibrator = Calibrator(mode=get_mocked_backend(), options=opts_dict)
        assert calibrator.options.experimental == {"foo": "bar", "baz": 123}

    def test_experimental_options_from_instance(self):
        """Test constructing with a CalibratorOptions instance with experimental options."""
        opts = CalibratorOptions(experimental={"custom_key": "custom_value"})
        calibrator = Calibrator(mode=get_mocked_backend(), options=opts)
        assert calibrator.options.experimental == {"custom_key": "custom_value"}

    def test_experimental_options_setter(self):
        """Test setting experimental options via the setter."""
        calibrator = Calibrator(mode=get_mocked_backend())
        calibrator.options = {"experimental": {"test": "value"}}
        assert calibrator.options.experimental == {"test": "value"}

    def test_validation_on_mutation(self):
        """Test validation errors are raised on mutation, not just construction."""
        options = ReadoutAngleOptions(enable=True)
        with self.assertRaises(ValidationError):
            options.enable = "not_a_bool"

    def test_extra_variables_are_forbidden(self):
        """Test that we can not set variables undefined by the model."""
        options = ReadoutAngleOptions()
        with self.assertRaises(ValidationError):
            options.not_a_variable = 0


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
        assert calibrator.backend() == backend
        assert calibrator.mode == expected_mode

        # Jobs issued should belong to a session under `session` / `batch` modes.
        job = calibrator.run()
        assert job._session_id == expected_session_id
