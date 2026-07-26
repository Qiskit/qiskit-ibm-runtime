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

"""Test QiskitRuntimeService."""

from __future__ import annotations

from qiskit_ibm_runtime.qiskit_runtime_service import QiskitRuntimeService

from ..decorators import mock_authentication
from ..ibm_test_case import IBMTestCase


class TestQiskitRuntimeServiceCase(IBMTestCase):
    """Tests for QiskitRuntimeService that use mocked HTTP responses."""

    @mock_authentication
    def test_authenticate_with_decorator(self, registry):
        """Test something."""
        service = QiskitRuntimeService(token="42")
        b = service.backends()
        print(b)
        print(service._backends_info_per_instance)
