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

"""Tests for Calibrator."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from qiskit_ibm_runtime import Session
from qiskit_ibm_runtime.calibrator import Calibrator
from qiskit_ibm_runtime.options_models.calibrator import CalibratorOptions
from qiskit_ibm_runtime.results import CalibratorResult

if TYPE_CHECKING:
    from .dependencies import Dependencies


@pytest.mark.skip(reason="This feature is not yet supported.")
class TestCalibrator:
    """Test Calibrator."""

    def test_calibrator(self, dependencies: Dependencies) -> None:
        """Test that a calibration job runs and returns a result."""
        backend = dependencies.service.backend(dependencies.qpu)

        with Session(backend=backend) as session:
            calibrator = Calibrator(session)
            calibrator.options.experimental = {"foo": "bar"}
            job = calibrator.run()
            result = job.result()

        inputs = job.inputs
        assert inputs["schema_version"] == "v0.1"
        assert isinstance(inputs["options"], CalibratorOptions)
        assert inputs["options"].experimental == calibrator.options.experimental

        assert isinstance(result, CalibratorResult)
        assert result.start < result.stop
