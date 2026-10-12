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

import unittest
from typing import TYPE_CHECKING

from qiskit_ibm_runtime import Session
from qiskit_ibm_runtime.calibrator import Calibrator

if TYPE_CHECKING:
    from .case import IntegrationTestDependencies


@unittest.skip("This feature is not yet supported.")
class TestCalibrator:
    """Test Calibrator."""

    def test_calibrator(self, dependencies: IntegrationTestDependencies) -> None:
        """Test that a calibration job runs and returns a result."""
        backend = dependencies.service.backend(dependencies.qpu)

        with Session(backend=backend) as session:
            calibrator = Calibrator(session)
            job = calibrator.run()
            result = job.result()
            assert "calibration_result" in result
