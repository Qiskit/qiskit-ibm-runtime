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
from qiskit_ibm_runtime.api.clients import AccountClient
from qiskit_ibm_runtime.api.exceptions import RequestsApiError

from .mock.http_server import SimpleServer, ClientErrorHandler
from ..ibm_test_case import IBMTestCase
from ..account import custom_envs, no_envs


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
            channel="ibm_quantum",
            url=SimpleServer.URL,
            token="foo",
            instance="h/g/p",
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
