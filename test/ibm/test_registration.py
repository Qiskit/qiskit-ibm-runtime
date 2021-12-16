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

"""Test the registration and credentials modules."""

from requests_ntlm import HttpNtlmAuth

from qiskit_ibm_runtime.credentials import (
    Credentials,
)
from ..ibm_test_case import IBMTestCase

IBM_TEMPLATE = "https://localhost/api/Hubs/{}/Groups/{}/Projects/{}"

PROXIES = {
    "urls": {
        "http": "http://user:password@127.0.0.1:5678",
        "https": "https://user:password@127.0.0.1:5678",
    }
}


class TestCredentialsKwargs(IBMTestCase):
    """Test for ``Credentials.connection_parameters()``."""

    def test_no_proxy_params(self) -> None:
        """Test when no proxy parameters are passed."""
        no_params_expected_result = {"verify": True}
        no_params_credentials = Credentials("dummy_token", "https://dummy_url")
        result = no_params_credentials.connection_parameters()
        self.assertDictEqual(no_params_expected_result, result)

    def test_verify_param(self) -> None:
        """Test 'verify' arg is acknowledged."""
        false_verify_expected_result = {"verify": False}
        false_verify_credentials = Credentials(
            "dummy_token", "https://dummy_url", verify=False
        )
        result = false_verify_credentials.connection_parameters()
        self.assertDictEqual(false_verify_expected_result, result)

    def test_proxy_param(self) -> None:
        """Test using only proxy urls (no NTLM credentials)."""
        urls = {"http": "localhost:8080", "https": "localhost:8080"}
        proxies_only_expected_result = {"verify": True, "proxies": urls}
        proxies_only_credentials = Credentials(
            "dummy_token", "https://dummy_url", proxies={"urls": urls}
        )
        result = proxies_only_credentials.connection_parameters()
        self.assertDictEqual(proxies_only_expected_result, result)

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
        proxies_with_ntlm_credentials = Credentials(
            "dummy_token", "https://dummy_url", proxies=proxies_with_ntlm_dict
        )
        result = proxies_with_ntlm_credentials.connection_parameters()

        # Verify the NTLM credentials.
        self.assertEqual(ntlm_expected_result["auth"].username, result["auth"].username)
        self.assertEqual(ntlm_expected_result["auth"].password, result["auth"].password)

        # Remove the HttpNtlmAuth objects for direct comparison of the dicts.
        ntlm_expected_result.pop("auth")
        result.pop("auth")
        self.assertDictEqual(ntlm_expected_result, result)

    def test_malformed_proxy_param(self) -> None:
        """Test input with malformed nesting of the proxies dictionary."""
        urls = {"http": "localhost:8080", "https": "localhost:8080"}
        malformed_nested_proxies_dict = {"proxies": urls}
        malformed_nested_credentials = Credentials(
            "dummy_token", "https://dummy_url", proxies=malformed_nested_proxies_dict
        )

        # Malformed proxy entries should be ignored.
        expected_result = {"verify": True}
        result = malformed_nested_credentials.connection_parameters()
        self.assertDictEqual(expected_result, result)

    def test_malformed_ntlm_params(self) -> None:
        """Test input with malformed NTLM credentials."""
        urls = {"http": "localhost:8080", "https": "localhost:8080"}
        malformed_ntlm_credentials_dict = {
            "urls": urls,
            "username_ntlm": 1234,
            "password_ntlm": 5678,
        }
        malformed_ntlm_credentials = Credentials(
            "dummy_token", "https://dummy_url", proxies=malformed_ntlm_credentials_dict
        )
        # Should raise when trying to do username.split('\\', <int>)
        # in NTLM credentials due to int not facilitating 'split'.
        with self.assertRaises(AttributeError):
            _ = malformed_ntlm_credentials.connection_parameters()
