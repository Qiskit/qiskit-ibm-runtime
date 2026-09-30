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

"""Tests for the RuntimeClient class."""

import responses
from ddt import data, ddt

from qiskit_ibm_runtime.api.client import RuntimeClient
from qiskit_ibm_runtime.api.client_parameters import ClientParameters
from qiskit_ibm_runtime.api.exceptions import RequestsApiError

from ..account import custom_envs, no_envs
from ..ibm_test_case import IBMTestCase


@ddt
class TestAccountClient(IBMTestCase):
    """Tests for RuntimeClient."""

    def _get_client(self):
        """Helper for instantiating an RuntimeClient."""
        return RuntimeClient(
            ClientParameters(
                channel="ibm_quantum_platform",
                url="https://quantum.cloud.ibm.com",
                token="foo",
                instance="crn",
            )
        )

    @data(
        {"error": "Bad client input"},
        {},
        {"bad request": "Bad client input"},
        "Bad client input",
    )
    @responses.activate
    def test_client_error(self, response):
        """Test client error."""
        responses.add(
            responses.GET,
            url="https://quantum.cloud.ibm.com/backends/ibmq_qasm_simulator/status",
            json=response,
            status=400,
        )

        responses.add(responses.POST, url="https://iam.cloud.ibm.com/identity/token", json=None)

        # self.fake_server.set_error_response(response)
        client = self._get_client()
        with self.assertRaises(RequestsApiError) as err_cm:
            with self.assertWarnsRegex(UserWarning, "Provided API key could not be found."):
                client.backend_status("ibmq_qasm_simulator")
        if response:
            self.assertIn("Bad client input", str(err_cm.exception))

    def test_custom_client_app_header(self):
        """Check custom client application header."""
        custom_header = "batman"
        with custom_envs({"QISKIT_IBM_RUNTIME_CUSTOM_CLIENT_APP_HEADER": custom_header}):
            client = self._get_client()
            client._session.headers.update({"X-Qx-Client-Application": "qiskit-version-2/qiskit"})
            client._session._set_custom_header()
            self.assertIn(custom_header, client._session.headers["X-Qx-Client-Application"])

        # Make sure the header is re-initialized
        with no_envs(["QISKIT_IBM_RUNTIME_CUSTOM_CLIENT_APP_HEADER"]):
            client = self._get_client()
            client._session.headers.update({"X-Qx-Client-Application": "qiskit-version-2/qiskit"})
            client._session.custom_header = None
            client._session._set_custom_header()
            self.assertNotIn(custom_header, client._session.headers["X-Qx-Client-Application"])

    def test_header_api_version(self):
        """Test IBM-API-Version is in header."""
        client = self._get_client()
        self.assertIn("IBM-API-Version", client._session.headers)
