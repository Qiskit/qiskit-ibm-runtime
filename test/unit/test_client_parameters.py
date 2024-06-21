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

"""Tests for ClientParameters."""

import uuid

from requests_ntlm import HttpNtlmAuth

from qiskit_ibm_runtime.proxies import ProxyConfiguration
from qiskit_ibm_runtime.api.client_parameters import ClientParameters
from qiskit_ibm_runtime.api.auth import CloudAuth, QuantumAuth

from ..ibm_test_case import IBMTestCase


class TestClientParameters(IBMTestCase):
    """Test for ``ClientParameters``."""

    def test_no_proxy_params(self) -> None:
        """Test when no proxy parameters are passed."""
        no_params_expected_result = {"verify": True}
        no_params_credentials = self._get_client_params()
        result = no_params_credentials.connection_parameters()
        self.assertDictEqual(no_params_expected_result, result)

    def test_verify_param(self) -> None:
        """Test 'verify' arg is acknowledged."""
        false_verify_expected_result = {"verify": False}
        false_verify_credentials = self._get_client_params(verify=False)
        result = false_verify_credentials.connection_parameters()
        self.assertDictEqual(false_verify_expected_result, result)

    def test_proxy_param(self) -> None:
        """Test using only proxy urls (no NTLM credentials)."""
        urls = {"http": "localhost:8080", "https": "localhost:8080"}
        proxies_only_expected_result = {"verify": True, "proxies": urls}
        proxies_only_credentials = self._get_client_params(
            proxies=ProxyConfiguration(**{"urls": urls})
        )
        result = proxies_only_credentials.connection_parameters()
        self.assertDictEqual(proxies_only_expected_result, result)

    def test_get_runtime_api_base_url(self) -> None:
        """Test resolution of runtime API base URL."""
        test_specs = [
            (
                "ibm_cloud",
                "crn:v1:bluemix:public:quantum-computing:us-east:a/...:...::",
                "https://cloud.ibm.com",
                "https://us-east.quantum-computing.cloud.ibm.com",
            ),
            (
                "ibm_cloud",
                "crn:v1:bluemix:public:quantum-computing:my-region:a/...:...::",
                "https://cloud.ibm.com",
                "https://my-region.quantum-computing.cloud.ibm.com",
            ),
            (
                "ibm_cloud",
                "crn:v1:bluemix:public:quantum-computing:my-region:a/...:...::",
                "https://api-ntc-name.experimental-us-someid.us-east.containers.appdomain.cloud",
                "https://api-ntc-name.experimental-us-someid.us-east.containers.appdomain.cloud",
            ),
            (
                "ibm_quantum",
                "h/g/p",
                "https://auth.quantum-computing.ibm.com/api",
                "https://auth.quantum-computing.ibm.com/api",
            ),
        ]
        for spec in test_specs:
            channel, instance, url, expected = spec
            with self.subTest(instance=instance, url=url):
                params = self._get_client_params(channel=channel, instance=instance, url=url)
                self.assertEqual(params.get_runtime_api_base_url(), expected)

    def test_proxies_param_with_ntlm(self) -> None:
        """Test proxies with NTLM credentials."""
        urls = {"http": "localhost:8080", "https": "localhost:8080"}
        proxies_with_ntlm_dict = {
            "urls": urls,
            "username_ntlm": "domain\\username",
            "password_ntlm": "password",
        }
        ntlm_expected_result = {
            "verify": True,
            "proxies": urls,
            "auth": HttpNtlmAuth("domain\\username", "password"),
        }
        proxies_with_ntlm_credentials = self._get_client_params(
            proxies=ProxyConfiguration(**proxies_with_ntlm_dict)
        )
        result = proxies_with_ntlm_credentials.connection_parameters()

        # Verify the NTLM credentials.
        self.assertEqual(ntlm_expected_result["auth"].username, result["auth"].username)
        self.assertEqual(ntlm_expected_result["auth"].password, result["auth"].password)

        # Remove the HttpNtlmAuth objects for direct comparison of the dicts.
        ntlm_expected_result.pop("auth")
        result.pop("auth")
        self.assertDictEqual(ntlm_expected_result, result)

    def test_malformed_ntlm_params(self) -> None:
        """Test input with malformed NTLM credentials."""
        urls = {"http": "localhost:8080", "https": "localhost:8080"}
        malformed_ntlm_credentials_dict = {
            "urls": urls,
            "username_ntlm": 1234,
            "password_ntlm": 5678,
        }
        malformed_ntlm_credentials = self._get_client_params(
            proxies=malformed_ntlm_credentials_dict
        )
        # Should raise when trying to do username.split('\\', <int>)
        # in NTLM credentials due to int not facilitating 'split'.
        with self.assertRaises(AttributeError):
            _ = malformed_ntlm_credentials.connection_parameters()

    def test_auth_handler_quantum(self):
        """Test getting quantum auth handler."""
        token = uuid.uuid4().hex
        params = self._get_client_params(channel="ibm_quantum", token=token)
        handler = params.get_auth_handler()
        self.assertIsInstance(handler, QuantumAuth)
        self.assertIn(token, handler.get_headers().values())

    def test_auth_handler_cloud(self):
        """Test getting cloud auth handler."""
        token = uuid.uuid4().hex
        instance = uuid.uuid4().hex
        params = self._get_client_params(channel="ibm_cloud", token=token, instance=instance)
        handler = params.get_auth_handler()
        self.assertIsInstance(handler, CloudAuth)
        self.assertIn(f"apikey {token}", handler.get_headers().values())
        self.assertIn(instance, handler.get_headers().values())

    def _get_client_params(
        self,
        channel="ibm_quantum",
        token="dummy_token",
        url="https://dummy_url",
        instance=None,
        proxies=None,
        verify=None,
    ):
        """Return a custom ClientParameters."""
        if verify is None:
            verify = True
        return ClientParameters(
            channel=channel,
            token=token,
            url=url,
            instance=instance,
            proxies=proxies,
            verify=verify,
        )
