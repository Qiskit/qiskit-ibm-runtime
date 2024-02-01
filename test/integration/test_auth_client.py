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

import re

from qiskit_ibm_runtime.api.exceptions import RequestsApiError
from qiskit_ibm_runtime.exceptions import IBMNotAuthorizedError
from qiskit_ibm_runtime.api.client_parameters import ClientParameters
from qiskit_ibm_runtime.api.clients import AuthClient
from ..ibm_test_case import IBMTestCase
from ..decorators import integration_test_setup, IntegrationTestDependencies


class TestAuthClient(IBMTestCase):
    """Tests for the AuthClient."""

    @integration_test_setup(supported_channel=["ibm_quantum"], init_service=False)
    def test_valid_login(self, dependencies: IntegrationTestDependencies) -> None:
        """Test valid authentication."""
        client = self._init_auth_client(dependencies.token, dependencies.url)
        self.assertTrue(client.access_token)

    @integration_test_setup(supported_channel=["ibm_quantum"], init_service=False)
    def test_url_404(self, dependencies: IntegrationTestDependencies) -> None:
        """Test login against a 404 URL"""
        url_404 = re.sub(r"/api.*$", "/api/TEST_404", dependencies.url)
        with self.assertRaises(RequestsApiError):
            _ = self._init_auth_client(dependencies.token, url_404)

    @integration_test_setup(supported_channel=["ibm_quantum"], init_service=False)
    def test_invalid_token(self, dependencies: IntegrationTestDependencies) -> None:
        """Test login using invalid token."""
        qe_token = "INVALID_TOKEN"
        with self.assertRaises(IBMNotAuthorizedError):
            _ = self._init_auth_client(qe_token, dependencies.url)

    @integration_test_setup(supported_channel=["ibm_quantum"], init_service=False)
    def test_url_unreachable(self, dependencies: IntegrationTestDependencies) -> None:
        """Test login against an invalid (malformed) URL."""
        qe_url = "INVALID_URL"
        with self.assertRaises(RequestsApiError):
            _ = self._init_auth_client(dependencies.token, qe_url)

    @integration_test_setup(supported_channel=["ibm_quantum"], init_service=False)
    def test_api_version(self, dependencies: IntegrationTestDependencies) -> None:
        """Check the version of the QX API."""
        client = self._init_auth_client(dependencies.token, dependencies.url)
        version = client.api_version()
        self.assertIsNotNone(version)

    @integration_test_setup(supported_channel=["ibm_quantum"], init_service=False)
    def test_user_urls(self, dependencies: IntegrationTestDependencies) -> None:
        """Check the user urls of the QX API."""
        client = self._init_auth_client(dependencies.token, dependencies.url)
        user_urls = client.user_urls()
        self.assertIsNotNone(user_urls)
        self.assertTrue("http" in user_urls and "ws" in user_urls)

    @integration_test_setup(supported_channel=["ibm_quantum"], init_service=False)
    def test_user_hubs(self, dependencies: IntegrationTestDependencies) -> None:
        """Check the user hubs of the QX API."""
        client = self._init_auth_client(dependencies.token, dependencies.url)
        user_hubs = client.user_hubs()
        self.assertIsNotNone(user_hubs)
        for user_hub in user_hubs:
            with self.subTest(user_hub=user_hub):
                self.assertTrue("hub" in user_hub and "group" in user_hub and "project" in user_hub)

    def _init_auth_client(self, token, url):
        """Return an AuthClient."""
        params = ClientParameters(channel="ibm_quantum", token=token, url=url)
        return AuthClient(params)
