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

"""Tests for the AccountClient class."""


from qiskit_ibm_runtime.api.client_parameters import ClientParameters

from ..ibm_test_case import IBMTestCase
from ..decorators import integration_test_setup, IntegrationTestDependencies


class TestAuthClient(IBMTestCase):
    """Tests for the AuthClient."""

    @integration_test_setup(supported_channel=["ibm_cloud"], init_service=False)
    def test_cloud_access_token(self, dependencies: IntegrationTestDependencies) -> None:
        """Test valid cloud authentication."""
        params = ClientParameters(
            channel="ibm_cloud",
            token=dependencies.token,
            url=dependencies.url,
            instance=dependencies.instance,
        )
        cloud_auth = params.get_auth_handler()
        self.assertTrue(cloud_auth.tm)
        self.assertTrue(cloud_auth.tm.get_token())
