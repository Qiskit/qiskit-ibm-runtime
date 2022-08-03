# This code is part of Qiskit.
#
# (C) Copyright IBM 2021.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Tests for Estimator class."""

from unittest.mock import MagicMock

from qiskit_ibm_runtime import Session, Estimator
from ..ibm_test_case import IBMTestCase


class TestEstimator(IBMTestCase):
    """Class for testing the Estimator class."""

    def test_estimator_new_session_old_call(self):
        """Test calling estimator with new session."""
        with Session(service=MagicMock()) as session:
            estimator = session.estimator()
            with self.assertRaises(ValueError):
                estimator(circuits=MagicMock(), observables=MagicMock())

    def test_estimator_old_session_new_call(self):
        """Test old session with new run method."""
        with Estimator(service=MagicMock()) as estimator:
            with self.assertRaises(ValueError):
                estimator.run(circuits=MagicMock(), observables=MagicMock())
