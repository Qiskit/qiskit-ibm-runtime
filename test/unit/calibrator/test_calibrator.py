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

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from qiskit_ibm_runtime.batch import Batch
from qiskit_ibm_runtime.calibrator import Calibrator
from qiskit_ibm_runtime.options_models.calibrator import CalibratorOptions
from qiskit_ibm_runtime.qiskit_runtime_service import QiskitRuntimeService
from qiskit_ibm_runtime.session import Session

from ...utils import get_mocked_backend

if TYPE_CHECKING:
    from ...registries import BaseRegistry


class TestCalibratorOptions:
    """Tests option setting on the ``Calibrator`` class."""

    def test_default_options(self) -> None:
        """Test that default options are set when none are provided."""
        calibrator = Calibrator(mode=get_mocked_backend())
        assert isinstance(calibrator.options, CalibratorOptions)
        assert calibrator.options == CalibratorOptions()

    def test_options_from_instance(self) -> None:
        """Test constructing with a CalibratorOptions instance."""
        opts = CalibratorOptions()
        calibrator = Calibrator(mode=get_mocked_backend(), options=opts)
        assert calibrator.options is opts

    def test_options_constructor_invalid_type(self) -> None:
        """Test that an invalid options type raises TypeError."""
        with pytest.raises(TypeError, match="Expected CalibratorOptions or dict"):
            Calibrator(mode=get_mocked_backend(), options="invalid")  # type: ignore[arg-type]

    def test_setter_invalid_type(self) -> None:
        """Test that setting options with an invalid type raises TypeError."""
        calibrator = Calibrator(mode=get_mocked_backend())
        with pytest.raises(TypeError, match="Expected CalibratorOptions or dict"):
            calibrator.options = 42  # type: ignore[assignment]

    def test_experimental_options_default_empty(self) -> None:
        """Test that experimental options default to empty dict."""
        calibrator = Calibrator(mode=get_mocked_backend())
        assert calibrator.options.experimental == {}

    def test_experimental_options_from_dict(self) -> None:
        """Test constructing with experimental options in dict."""
        opts_dict = {"experimental": {"foo": "bar", "baz": 123}}
        calibrator = Calibrator(mode=get_mocked_backend(), options=opts_dict)
        assert calibrator.options.experimental == {"foo": "bar", "baz": 123}

    def test_experimental_options_from_instance(self) -> None:
        """Test constructing with a CalibratorOptions instance with experimental options."""
        opts = CalibratorOptions(experimental={"custom_key": "custom_value"})
        calibrator = Calibrator(mode=get_mocked_backend(), options=opts)
        assert calibrator.options.experimental == {"custom_key": "custom_value"}

    def test_experimental_options_setter(self) -> None:
        """Test setting experimental options via the setter."""
        calibrator = Calibrator(mode=get_mocked_backend())
        calibrator.options = {"experimental": {"test": "value"}}  # type: ignore[assignment]
        assert calibrator.options.experimental == {"test": "value"}


class TestCalibrator:
    """Tests the ``Calibrator`` class."""

    @pytest.mark.parametrize("mode_id", ["job", "session", "batch"])
    def test_mode_handling(self, mode_id: str, registry: BaseRegistry) -> None:
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
