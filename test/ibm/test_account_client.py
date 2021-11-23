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

from qiskit.circuit import ClassicalRegister, QuantumCircuit, QuantumRegister
from qiskit_ibm_runtime.api.clients import AccountClient, AuthClient
from qiskit_ibm_runtime.api.exceptions import ApiError, RequestsApiError

from ..ibm_test_case import IBMTestCase
from ..decorators import requires_qe_access, requires_provider
from ..contextmanagers import custom_envs, no_envs
from ..http_server import SimpleServer, ClientErrorHandler


class TestAccountClient(IBMTestCase):
    """Tests for AccountClient."""

    @classmethod
    @requires_provider
    def setUpClass(cls, service, hub, group, project):
        """Initial class level setup."""
        # pylint: disable=arguments-differ
        super().setUpClass()
        cls.service = service
        cls.hub = hub
        cls.group = group
        cls.project = project
        default_hgp = cls.service._default_hgp
        cls.access_token = default_hgp._api_client.account_api.session._access_token

    def setUp(self):
        """Initial test setup."""
        super().setUp()
        qr = QuantumRegister(2)
        cr = ClassicalRegister(2)
        self.qc1 = QuantumCircuit(qr, cr, name='qc1')
        self.qc2 = QuantumCircuit(qr, cr, name='qc2')
        self.qc1.h(qr)
        self.qc2.h(qr[0])
        self.qc2.cx(qr[0], qr[1])
        self.qc1.measure(qr[0], cr[0])
        self.qc1.measure(qr[1], cr[1])
        self.qc2.measure(qr[0], cr[0])
        self.qc2.measure(qr[1], cr[1])
        self.seed = 73846087

        self.fake_server = None

    def tearDown(self) -> None:
        """Test level tear down."""
        super().tearDown()
        if self.fake_server:
            self.fake_server.stop()

    def _get_client(self):
        """Helper for instantiating an AccountClient."""
        # pylint: disable=no-value-for-parameter
        return AccountClient(self.service._default_hgp.credentials)

    def test_custom_client_app_header(self):
        """Check custom client application header."""
        custom_header = 'batman'
        with custom_envs({'QISKIT_IBM_RUNTIME_CUSTOM_CLIENT_APP_HEADER': custom_header}):
            client = self._get_client()
            self.assertIn(custom_header,
                          client._session.headers['X-Qx-Client-Application'])

        # Make sure the header is re-initialized
        with no_envs(['QISKIT_IBM_RUNTIME_CUSTOM_CLIENT_APP_HEADER']):
            client = self._get_client()
            self.assertNotIn(custom_header,
                             client._session.headers['X-Qx-Client-Application'])

    def test_client_error(self):
        """Test client error."""
        client = self._get_client()
        self.fake_server = SimpleServer(handler_class=ClientErrorHandler)
        self.fake_server.start()
        client.account_api.session.base_url = SimpleServer.URL

        sub_tests = [{'error': 'Bad client input'},
                     {},
                     {'bad request': 'Bad client input'},
                     'Bad client input']

        for err_resp in sub_tests:
            with self.subTest(response=err_resp):
                self.fake_server.set_error_response(err_resp)
                with self.assertRaises(RequestsApiError) as err_cm:
                    client.backend_status('ibmq_qasm_simulator')
                if err_resp:
                    self.assertIn('Bad client input', str(err_cm.exception))


class TestAuthClient(IBMTestCase):
    """Tests for the AuthClient."""

    @requires_qe_access
    def test_valid_login(self, qe_token, qe_url):
        """Test valid authentication."""
        client = AuthClient(qe_token, qe_url)
        self.assertTrue(client.base_api.session._access_token)

    @requires_qe_access
    def test_url_404(self, qe_token, qe_url):
        """Test login against a 404 URL"""
        url_404 = re.sub(r'/api.*$', '/api/TEST_404', qe_url)
        with self.assertRaises(ApiError):
            _ = AuthClient(qe_token, url_404)

    @requires_qe_access
    def test_invalid_token(self, qe_token, qe_url):
        """Test login using invalid token."""
        qe_token = 'INVALID_TOKEN'
        with self.assertRaises(ApiError):
            _ = AuthClient(qe_token, qe_url)

    @requires_qe_access
    def test_url_unreachable(self, qe_token, qe_url):
        """Test login against an invalid (malformed) URL."""
        qe_url = 'INVALID_URL'
        with self.assertRaises(ApiError):
            _ = AuthClient(qe_token, qe_url)

    @requires_qe_access
    def test_api_version(self, qe_token, qe_url):
        """Check the version of the QX API."""
        client = AuthClient(qe_token, qe_url)
        version = client.api_version()
        self.assertIsNotNone(version)

    @requires_qe_access
    def test_user_urls(self, qe_token, qe_url):
        """Check the user urls of the QX API."""
        client = AuthClient(qe_token, qe_url)
        user_urls = client.user_urls()
        self.assertIsNotNone(user_urls)
        self.assertTrue('http' in user_urls and 'ws' in user_urls)

    @requires_qe_access
    def test_user_hubs(self, qe_token, qe_url):
        """Check the user hubs of the QX API."""
        client = AuthClient(qe_token, qe_url)
        user_hubs = client.user_hubs()
        self.assertIsNotNone(user_hubs)
        for user_hub in user_hubs:
            with self.subTest(user_hub=user_hub):
                self.assertTrue('hub' in user_hub
                                and 'group' in user_hub
                                and 'project' in user_hub)
