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

"""Tests for Batch class."""

from unittest.mock import patch

from qiskit_ibm_runtime import Batch
from qiskit_ibm_runtime.utils.default_session import _DEFAULT_SESSION

from ..ibm_test_case import IBMTestCase


class TestBatch(IBMTestCase):
    """Class for testing the Session class."""

    def tearDown(self) -> None:
        super().tearDown()
        _DEFAULT_SESSION.set(None)

    @patch("qiskit_ibm_runtime.session.QiskitRuntimeService", autospec=True)
    def test_default_batch(self, mock_service):
        """Test using default batch mode."""
        mock_service.global_service = None
        batch = Batch(backend="ibm_gotham")
        self.assertIsNotNone(batch.service)
        mock_service.assert_called_once()
