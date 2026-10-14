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

import pytest
import responses

from qiskit_ibm_runtime.api.client import RuntimeClient
from qiskit_ibm_runtime.api.client_parameters import ClientParameters
from qiskit_ibm_runtime.api.exceptions import RequestsApiError

from ..account import custom_envs, no_envs


def runtime_client() -> RuntimeClient:
    """Helper for instantiating an RuntimeClient."""
    return RuntimeClient(
        ClientParameters(
            channel="ibm_quantum_platform",
            url="https://quantum.cloud.ibm.com",
            token="foo",
            instance="crn",
        )
    )


class TestAccountClient:
    """Tests for RuntimeClient."""

    @pytest.mark.parametrize(
        "response",
        [
            {"error": "Bad client input"},
            {},
            {"bad request": "Bad client input"},
            "Bad client input",
        ],
    )
    @responses.activate
    def test_client_error(self, response: dict | str) -> None:
        """Test client error."""
        responses.add(
            responses.GET,
            url="https://quantum.cloud.ibm.com/backends/ibmq_qasm_simulator/status",
            json=response,
            status=400,
        )

        responses.add(responses.POST, url="https://iam.cloud.ibm.com/identity/token", json=None)

        client = runtime_client()
        with pytest.raises(RequestsApiError) as err_cm:
            with pytest.warns(UserWarning, match="Unable to retrieve"):
                client.backend_status("ibmq_qasm_simulator")
        if response:
            assert "Bad client input" in str(err_cm.value)

    def test_custom_client_app_header(self) -> None:
        """Check custom client application header."""
        custom_header = "batman"
        with custom_envs({"QISKIT_IBM_RUNTIME_CUSTOM_CLIENT_APP_HEADER": custom_header}):
            client = runtime_client()
            client._session.headers.update({"X-Qx-Client-Application": "qiskit-version-2/qiskit"})
            client._session._set_custom_header()
            assert custom_header in client._session.headers["X-Qx-Client-Application"]

        # Make sure the header is re-initialized
        with no_envs(["QISKIT_IBM_RUNTIME_CUSTOM_CLIENT_APP_HEADER"]):
            client = runtime_client()
            client._session.headers.update({"X-Qx-Client-Application": "qiskit-version-2/qiskit"})
            client._session.custom_header = None
            client._session._set_custom_header()
            assert custom_header not in client._session.headers["X-Qx-Client-Application"]

    def test_header_api_version(self) -> None:
        """Test IBM-API-Version is in header."""
        client = runtime_client()
        assert "IBM-API-Version" in client._session.headers
