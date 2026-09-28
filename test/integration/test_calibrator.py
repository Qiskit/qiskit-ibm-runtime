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

import unittest

from qiskit_ibm_runtime.calibrator import Calibrator

from ..ibm_test_case import IBMIntegrationTestCase


@unittest.skip("This feature is not yet supported.")
class TestCalibrator(IBMIntegrationTestCase):
    """Test Calibrator."""

    def setUp(self):
        """Test level setup."""
        super().setUp()
        self.backend = self.service.backend(self.dependencies.qpu)

    def test_calibrator(self):
        """Test that a calibration job runs and returns a result."""
        calibrator = Calibrator(self.backend)
        job = calibrator.run()
        result = job.result()
        self.assertIn("calibration_result", result)
