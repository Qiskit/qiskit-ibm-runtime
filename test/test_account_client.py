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

from qiskit_ibm_runtime.api.clients import AccountClient, AuthClient
from qiskit_ibm_runtime.api.exceptions import ApiError, RequestsApiError
from qiskit_ibm_runtime.api.client_parameters import ClientParameters

from .ibm_test_case import IBMTestCase
from .mock.http_server import SimpleServer, ClientErrorHandler
from .utils.account import custom_envs, no_envs
from .utils.decorators import integration_test_setup, IntegrationTestDependencies


class TestAccountClient(IBMTestCase):
    """Tests for AccountClient."""

    def setUp(self):
        """Initial test setup."""
        super().setUp()
        self.fake_server = None

    def tearDown(self) -> None:
        """Test level tear down."""
        super().tearDown()
        if self.fake_server:
            self.fake_server.stop()

    def _get_client(self):
        """Helper for instantiating an AccountClient."""
        # pylint: disable=no-value-for-parameter
        params = ClientParameters(
            auth_type="legacy", url=SimpleServer.URL, token="foo", instance="h/g/p"
        )
        return AccountClient(params)

    def test_custom_client_app_header(self):
        """Check custom client application header."""
        custom_header = "batman"
        with custom_envs(
            {"QISKIT_IBM_RUNTIME_CUSTOM_CLIENT_APP_HEADER": custom_header}
        ):
            client = self._get_client()
            self.assertIn(
                custom_header, client._session.headers["X-Qx-Client-Application"]
            )

        # Make sure the header is re-initialized
        with no_envs(["QISKIT_IBM_RUNTIME_CUSTOM_CLIENT_APP_HEADER"]):
            client = self._get_client()
            self.assertNotIn(
                custom_header, client._session.headers["X-Qx-Client-Application"]
            )

    def test_client_error(self):
        """Test client error."""
        client = self._get_client()
        self.fake_server = SimpleServer(handler_class=ClientErrorHandler)
        self.fake_server.start()
        # client.account_api.session.base_url = SimpleServer.URL

        sub_tests = [
            {"error": "Bad client input"},
            {},
            {"bad request": "Bad client input"},
            "Bad client input",
        ]

        for err_resp in sub_tests:
            with self.subTest(response=err_resp):
                self.fake_server.set_error_response(err_resp)
                with self.assertRaises(RequestsApiError) as err_cm:
                    client.backend_status("ibmq_qasm_simulator")
                if err_resp:
                    self.assertIn("Bad client input", str(err_cm.exception))


class TestAuthClient(IBMTestCase):
    """Tests for the AuthClient."""

    @integration_test_setup(supported_auth=["legacy"], init_service=False)
    def test_valid_login(self, dependencies: IntegrationTestDependencies):
        """Test valid authentication."""
        client = self._init_auth_client(dependencies.token, dependencies.url)
        self.assertTrue(client.access_token)

    @integration_test_setup(supported_auth=["legacy"], init_service=False)
    def test_url_404(self, dependencies: IntegrationTestDependencies):
        """Test login against a 404 URL"""
        url_404 = re.sub(r"/api.*$", "/api/TEST_404", dependencies.url)
        with self.assertRaises(ApiError):
            _ = self._init_auth_client(dependencies.token, url_404)

    @integration_test_setup(supported_auth=["legacy"], init_service=False)
    def test_invalid_token(self, dependencies: IntegrationTestDependencies):
        """Test login using invalid token."""
        qe_token = "INVALID_TOKEN"
        with self.assertRaises(ApiError):
            _ = self._init_auth_client(qe_token, dependencies.url)

    @integration_test_setup(supported_auth=["legacy"], init_service=False)
    def test_url_unreachable(self, dependencies: IntegrationTestDependencies):
        """Test login against an invalid (malformed) URL."""
        qe_url = "INVALID_URL"
        with self.assertRaises(ApiError):
            _ = self._init_auth_client(dependencies.token, qe_url)

    @integration_test_setup(supported_auth=["legacy"], init_service=False)
    def test_api_version(self, dependencies: IntegrationTestDependencies):
        """Check the version of the QX API."""
        client = self._init_auth_client(dependencies.token, dependencies.url)
        version = client.api_version()
        self.assertIsNotNone(version)

    @integration_test_setup(supported_auth=["legacy"], init_service=False)
    def test_user_urls(self, dependencies: IntegrationTestDependencies):
        """Check the user urls of the QX API."""
        client = self._init_auth_client(dependencies.token, dependencies.url)
        user_urls = client.user_urls()
        self.assertIsNotNone(user_urls)
        self.assertTrue("http" in user_urls and "ws" in user_urls)

    @integration_test_setup(supported_auth=["legacy"], init_service=False)
    def test_user_hubs(self, dependencies: IntegrationTestDependencies):
        """Check the user hubs of the QX API."""
        client = self._init_auth_client(dependencies.token, dependencies.url)
        user_hubs = client.user_hubs()
        self.assertIsNotNone(user_hubs)
        for user_hub in user_hubs:
            with self.subTest(user_hub=user_hub):
                self.assertTrue(
                    "hub" in user_hub and "group" in user_hub and "project" in user_hub
                )

    def _init_auth_client(self, token, url):
        """Return an AuthClient."""
        params = ClientParameters(auth_type="legacy", token=token, url=url)
        return AuthClient(params)
