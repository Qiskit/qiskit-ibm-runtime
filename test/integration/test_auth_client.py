# This code is part of Qiskit.
#
# (C) Copyright IBM 2021-2026.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Tests for the AccountClient class."""

from __future__ import annotations

from qiskit_ibm_runtime.api.client_parameters import ClientParameters

from ..ibm_test_case import IBMTestCase
from .case import integration_test_dependencies


class TestAuthClient(IBMTestCase):
    """Tests for the AuthClient."""

    def test_cloud_access_token(self) -> None:
        """Test valid cloud authentication."""
        dependencies = integration_test_dependencies(init_service=False)
        params = ClientParameters(
            channel="ibm_cloud",
            token=dependencies.token,
            url=dependencies.url,
            instance=dependencies.instance,
        )
        cloud_auth = params.get_auth_handler()
        assert cloud_auth.tm
        assert cloud_auth.tm.get_token()
