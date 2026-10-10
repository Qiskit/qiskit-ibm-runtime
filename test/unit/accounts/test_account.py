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

"""Tests for the account functions."""

import copy
import logging
import os
import uuid
from typing import Any
from unittest import skipIf

from ddt import data, ddt
from requests.exceptions import ProxyError

from qiskit_ibm_runtime import IBMInputValueError
from qiskit_ibm_runtime.accounts import Account, AccountNotFoundError, InvalidAccountError
from qiskit_ibm_runtime.accounts.account import IBM_QUANTUM_PLATFORM_API_URL
from qiskit_ibm_runtime.proxies import ProxyConfiguration
from qiskit_ibm_runtime.qiskit_runtime_service import QiskitRuntimeService

from ...account import (
    custom_envs,
    get_account_config_contents,
    no_envs,
    temporary_account_config_file,
)
from ...decorators import mock_responses
from ...ibm_test_case import IBMTestCase
from ...utils import combine

_TEST_IBM_CLOUD_ACCOUNT = Account.create_account(
    channel="ibm_cloud",
    token="token-y",
    url="https://cloud.ibm.com",
    instance="crn:v1:bluemix:public:quantum-computing:us-east:a/...::",
    proxies=ProxyConfiguration(
        username_ntlm="bla", password_ntlm="blub", urls={"https": "127.0.0.1"}
    ),
)
_TEST_IBM_QUANTUM_PLATFORM_ACCOUNT = Account.create_account(
    channel="ibm_quantum_platform",
    token="token-y",
    url="https://quantum.cloud.ibm.com/api/v1",
    instance="crn:v1:bluemix:public:quantum-computing:us-east:a/...::",
    proxies=ProxyConfiguration(
        username_ntlm="bla", password_ntlm="blub", urls={"https": "127.0.0.1"}
    ),
)
_DEFAULT_CRN = "crn:v1:bluemix:public:quantum-computing:my-region:a/...:...::"

MOCK_PROXY_CONFIG_DICT = {"urls": {"https": "127.0.0.1", "username_ntlm": "", "password_ntlm": ""}}

DUMMY_TOKEN = "123"
DUMMY_IBM_CLOUD_URL = "https://quantum.cloud.ibm.com"


def assert_preferences(prefs, account):
    """Assert that the preferences set in `prefs` match the ones of `account`."""
    if "proxies" in prefs:
        assert account.proxies == ProxyConfiguration(**prefs["proxies"])
    if "verify" in prefs:
        assert account.verify == prefs["verify"]
    if "instance" in prefs:
        assert account.instance == prefs["instance"]


@ddt
class TestAccount(IBMTestCase):
    """Tests for Account class."""

    @data(_TEST_IBM_CLOUD_ACCOUNT, _TEST_IBM_QUANTUM_PLATFORM_ACCOUNT)
    def test_skip_crn_resolution_for_crn(self, test_account):
        """Test that CRN resolution is skipped if the instance value is already a CRN."""
        account = copy.deepcopy(test_account)
        account.resolve_crn()
        assert account.instance == test_account.instance

    def test_resolve_crn_proxied(self):
        """Account.resolve_crn() should go through proxies if specified."""
        account = Account.create_account(
            channel="ibm_quantum_platform",
            token="my_token",
            proxies=ProxyConfiguration(**MOCK_PROXY_CONFIG_DICT),
        )
        with self.assertRaises(ProxyError):
            # Requests go through a proxy, which is not available in this test.
            account.resolve_crn()

    def test_invalid_channel(self):
        """Test invalid values for channel parameter."""
        with self.assertRaises(InvalidAccountError) as err:
            invalid_channel: Any = "phantom"
            Account.create_account(
                channel=invalid_channel,
                token=DUMMY_TOKEN,
                url=DUMMY_IBM_CLOUD_URL,
            ).validate()
        assert "Invalid `channel` value." in str(err.exception)

    @data(1, None, "")
    def test_invalid_token(self, token):
        """Test invalid values for token parameter."""
        with self.assertRaises(InvalidAccountError) as err:
            Account.create_account(
                channel="ibm_cloud",
                token=token,
                url=DUMMY_IBM_CLOUD_URL,
            ).validate()
        assert "Invalid `token` value." in str(err.exception)

    def test_invalid_url(self):
        """Test invalid values for url parameter."""
        invalid_url: Any = 123

        with self.assertRaises(InvalidAccountError) as err:
            Account.create_account(
                channel="ibm_cloud",
                token=DUMMY_TOKEN,
                url=invalid_url,
            ).validate()
        assert "Invalid `url` value." in str(err.exception)

    def test_invalid_account_prefs(self):
        """Test invalid values for account preferences."""
        with self.assertRaises(InvalidAccountError) as err:
            Account.create_account(
                channel="ibm_quantum_platform",
                token=DUMMY_TOKEN,
                url=DUMMY_IBM_CLOUD_URL,
                region="invalid-region",
            ).validate()
        assert "Invalid `region` value." in str(err.exception)

        with self.assertRaises(InvalidAccountError) as err:
            Account.create_account(
                channel="ibm_quantum_platform",
                token=DUMMY_TOKEN,
                url=DUMMY_IBM_CLOUD_URL,
                plans_preference="invalid-plans",
            ).validate()
        assert "Invalid `plans_preference` value." in str(err.exception)

        with self.assertRaises(InvalidAccountError) as err:
            Account.create_account(
                channel="ibm_quantum_platform",
                token=DUMMY_TOKEN,
                url=DUMMY_IBM_CLOUD_URL,
                tags="invalid-tags",
            ).validate()
        assert "Invalid `tags` value." in str(err.exception)


# NamedTemporaryFiles not supported in Windows
@skipIf(os.name == "nt", "Test not supported in Windows")
@ddt
class TestEnableAccount(IBMTestCase):
    """Tests for QiskitRuntimeService enable account."""

    @mock_responses
    def test_enable_account_by_name(self, registry):
        """Test initializing account by name."""
        name = "foo"
        token = uuid.uuid4().hex
        with temporary_account_config_file(name=name, token=token):
            service = QiskitRuntimeService(name=name)

        assert service._account
        assert service._account.token == token

    @mock_responses
    @data("ibm_quantum_platform", "ibm_cloud")
    def test_enable_account_by_channel(self, channel, registry):
        """Test initializing account by channel."""
        with no_envs(["QISKIT_IBM_TOKEN"]):
            token = uuid.uuid4().hex
            with temporary_account_config_file(channel=channel, token=token):
                service = QiskitRuntimeService(channel=channel)
            assert service._account
            assert service._account.token == token

    @mock_responses
    @data(
        {"token": uuid.uuid4().hex}, {"token": uuid.uuid4().hex, "url": "https://foo.cloud.ibm.com"}
    )
    def test_enable_account_by_token_url(self, params, registry):
        """Test initializing account by token."""
        with temporary_account_config_file(channel="ibm_quantum_platform", token=params["token"]):
            service = QiskitRuntimeService(**params)
            assert service._account

    def test_enable_account_by_url_error(self):
        """Test initializing account by url gives an error."""
        token = uuid.uuid4().hex
        with temporary_account_config_file(channel="ibm_quantum_platform", token=token):
            with self.assertRaisesRegex(ValueError, "not valid as a standalone parameter"):
                QiskitRuntimeService(url="some_url")

    @mock_responses
    @data(
        {"channel": "ibm_cloud"},
        {"token": "some_token"},
        {"url": "some_url"},
        {"channel": "ibm_cloud", "token": "some_token", "url": "some_url"},
    )
    def test_enable_account_by_name_and_other(self, params, registry):
        """Test initializing account by name and other."""
        name = "foo"
        token = uuid.uuid4().hex
        with temporary_account_config_file(name=name, token=token):
            with self.assertLogs("qiskit_ibm_runtime", logging.WARNING) as logged:
                service = QiskitRuntimeService(name=name, **params)

            assert service._account
            assert service._account.token == token
            assert "are ignored" in logged.output[0]

    @mock_responses
    @data(None, "https://foo.cloud.ibm.com")
    def test_enable_cloud_account_by_channel_token_url(self, url, registry):
        """Test initializing cloud account by channel, token, url."""
        with no_envs(["QISKIT_IBM_TOKEN"]):
            token = uuid.uuid4().hex
            service = QiskitRuntimeService(channel="ibm_quantum_platform", token=token, url=url)
            assert service

    @mock_responses
    @data("ibm_quantum_platform", "ibm_cloud")
    def test_enable_account_by_channel_url(self, channel, registry):
        """Test initializing account by channel, token, url."""
        token = uuid.uuid4().hex
        with (
            temporary_account_config_file(channel=channel, token=token),
            no_envs(["QISKIT_IBM_TOKEN"]),
        ):
            with self.assertLogs("qiskit_ibm_runtime", logging.WARNING) as logged:
                service = QiskitRuntimeService(channel=channel, url="some_url")

        assert service._account
        assert service._account.token == token
        expected = IBM_QUANTUM_PLATFORM_API_URL
        assert service._account.url == expected
        assert "url" in logged.output[0]

    @mock_responses
    @data("ibm_quantum_platform", "ibm_cloud")
    def test_enable_account_by_only_channel(self, channel, registry):
        """Test initializing account with single saved account."""
        token = uuid.uuid4().hex
        with (
            temporary_account_config_file(channel=channel, token=token),
            no_envs(["QISKIT_IBM_TOKEN"]),
        ):
            service = QiskitRuntimeService()
        assert service._account
        assert service._account.token == token
        expected = IBM_QUANTUM_PLATFORM_API_URL
        assert service._account.url == expected
        assert service._account.channel == channel

    @mock_responses
    def test_enable_account_both_channel(self, registry):
        """Test initializing account with both saved types."""
        token = uuid.uuid4().hex
        contents = get_account_config_contents(channel="ibm_quantum_platform", token=token)

        with (
            temporary_account_config_file(contents=contents),
            no_envs(["QISKIT_IBM_TOKEN", "QISKIT_IBM_CHANNEL"]),
        ):
            service = QiskitRuntimeService()
        assert service._account
        assert service._account.token == token
        assert service._account.url == IBM_QUANTUM_PLATFORM_API_URL
        assert service._account.channel == "ibm_quantum_platform"

    @mock_responses
    @data("ibm_quantum_platform", "ibm_cloud", None)
    def test_enable_account_by_env_channel(self, channel, registry):
        """Test initializing account by environment variable and channel."""
        token = uuid.uuid4().hex
        url = "https://foo.cloud.ibm.com"
        envs = {
            "QISKIT_IBM_TOKEN": token,
            "QISKIT_IBM_URL": url,
            "QISKIT_IBM_INSTANCE": _DEFAULT_CRN,
        }
        with custom_envs(envs), no_envs("QISKIT_IBM_CHANNEL"):
            service = QiskitRuntimeService(channel=channel)

        assert service._account
        assert service._account.token == token
        assert service._account.url == url
        channel = channel or "ibm_quantum_platform"
        assert service._account.channel == channel

    @mock_responses
    @data("ibm_quantum_platform", "ibm_cloud", None)
    def test_enable_account_only_env_variables(self, channel, registry):
        """Test initializing account with only environment variables."""
        token = uuid.uuid4().hex
        url = "https://foo.cloud.ibm.com"
        envs = {
            "QISKIT_IBM_TOKEN": token,
            "QISKIT_IBM_URL": url,
            "QISKIT_IBM_CHANNEL": channel,
            "QISKIT_IBM_INSTANCE": _DEFAULT_CRN,
        }
        with custom_envs(envs):
            service = QiskitRuntimeService()
        assert service._account.channel == (channel or "ibm_quantum_platform")
        assert service._account.url == url

    @mock_responses
    @data(
        {"token": uuid.uuid4().hex}, {"token": uuid.uuid4().hex, "url": "https://foo.cloud.ibm.com"}
    )
    def test_enable_account_by_env_token_url(self, params, registry):
        """Test initializing account by environment variable and extra."""
        token = params["token"]
        url = "https://foo.cloud.ibm.com"
        envs = {
            "QISKIT_IBM_TOKEN": token,
            "QISKIT_IBM_URL": url,
            "QISKIT_IBM_INSTANCE": _DEFAULT_CRN,
        }
        with custom_envs(envs) as _:
            service = QiskitRuntimeService(**params)
            assert service._account

    def test_enable_account_bad_name(self):
        """Test initializing account by bad name."""
        name = "phantom"
        with temporary_account_config_file():
            with self.assertRaisesRegex(AccountNotFoundError, f"Account with the name {name}"):
                _ = QiskitRuntimeService(name=name)

    def test_enable_account_bad_channel(self):
        """Test initializing account by bad name."""
        channel = "phantom"
        with temporary_account_config_file():
            with self.assertRaisesRegex(ValueError, "'channel' can only be"):
                QiskitRuntimeService(channel=channel)

    @mock_responses
    @data(
        {"proxies": MOCK_PROXY_CONFIG_DICT},
        {"verify": False},
        {"instance": _DEFAULT_CRN},
        {"proxies": MOCK_PROXY_CONFIG_DICT, "verify": False, "instance": _DEFAULT_CRN},
    )
    def test_enable_account_by_name_pref(self, params, registry):
        """Test initializing account by name and preferences."""
        name = "foo"
        with temporary_account_config_file(name=name, verify=True, proxies={}):
            service = QiskitRuntimeService(name=name, **params)
        assert service._account
        assert_preferences(params, service._account)

    @mock_responses
    @combine(
        channel=["ibm_quantum_platform", "ibm_cloud"],
        params=[
            {"proxies": MOCK_PROXY_CONFIG_DICT},
            {"verify": False},
            {"instance": _DEFAULT_CRN},
            {"proxies": MOCK_PROXY_CONFIG_DICT, "verify": False, "instance": _DEFAULT_CRN},
        ],
    )
    def test_enable_account_by_channel_pref(self, channel, params, registry):
        """Test initializing account by channel and preferences."""
        with (
            temporary_account_config_file(channel=channel, verify=True, proxies={}),
            no_envs(["QISKIT_IBM_TOKEN"]),
        ):
            service = QiskitRuntimeService(channel=channel, **params)
            assert service._account
            assert_preferences(params, service._account)

    @mock_responses
    @data(
        {"proxies": MOCK_PROXY_CONFIG_DICT},
        {"verify": False},
        {"instance": _DEFAULT_CRN},
        {"proxies": MOCK_PROXY_CONFIG_DICT, "verify": False, "instance": _DEFAULT_CRN},
    )
    def test_enable_account_by_env_pref(self, params, registry):
        """Test initializing account by environment variable and preferences."""
        token = uuid.uuid4().hex
        url = "https://foo.cloud.ibm.com"
        envs = {
            "QISKIT_IBM_TOKEN": token,
            "QISKIT_IBM_URL": url,
            "QISKIT_IBM_INSTANCE": _DEFAULT_CRN,
        }
        with custom_envs(envs), no_envs("QISKIT_IBM_CHANNEL"):
            service = QiskitRuntimeService(**params)

        assert service._account
        assert_preferences(params, service._account)

    @mock_responses
    def test_enable_account_by_name_input_instance(self, registry):
        """Test initializing account by name and input instance."""
        name = "foo"
        instance = _DEFAULT_CRN
        with temporary_account_config_file(name=name, instance="stored-instance"):
            service = QiskitRuntimeService(name=name, instance=instance)
        assert service._account
        assert service._account.instance == instance

    @mock_responses
    def test_enable_account_by_channel_input_instance(self, registry):
        """Test initializing account by channel and input instance."""
        instance = _DEFAULT_CRN
        with temporary_account_config_file(channel="ibm_quantum_platform", instance="bla"):
            service = QiskitRuntimeService(channel="ibm_quantum_platform", instance=instance)
        assert service._account
        assert service._account.instance == instance

    @mock_responses
    def test_enable_account_by_env_input_instance(self, registry):
        """Test initializing account by env and input instance."""
        instance = _DEFAULT_CRN
        envs = {
            "QISKIT_IBM_TOKEN": "some_token",
            "QISKIT_IBM_URL": "https://foo.cloud.ibm.com",
            "QISKIT_IBM_INSTANCE": _DEFAULT_CRN,
        }
        with custom_envs(envs):
            service = QiskitRuntimeService(channel="ibm_cloud", instance=instance)
        assert service._account
        assert service._account.instance == instance

    @mock_responses
    def test_instance_filter_tags(self, registry):
        """Test initializing account by channel and input instance."""
        registry.instances["a"].tags = ["services"]

        tags = ["services"]
        with temporary_account_config_file(channel="ibm_quantum_platform"):
            service = QiskitRuntimeService(channel="ibm_quantum_platform", tags=tags)
            assert service._account
            for inst in service._backend_instance_groups:
                assert inst["tags"] == tags

            with self.assertRaisesRegex(IBMInputValueError, "No matching instances"):
                service = QiskitRuntimeService(
                    channel="ibm_quantum_platform", tags=["invalid_tags"]
                )

    @mock_responses
    def test_wrong_instance(self, registry):
        """Test an instance from a different account."""
        instance = "wrong_instance"
        with temporary_account_config_file(channel="ibm_quantum_platform"):
            with self.assertRaisesRegex(IBMInputValueError, "not a valid instance name"):
                QiskitRuntimeService(channel="ibm_quantum_platform", instance=instance)

    @mock_responses
    def test_instance_auto_flag_set(self, registry):
        """instance='auto' sets _instance_auto and leaves account.instance as None."""
        service = QiskitRuntimeService(
            channel="ibm_quantum_platform", token="my_token", instance="auto"
        )
        assert service._instance_auto
        assert service._account.instance is None

    @mock_responses
    def test_instance_auto_suppresses_init_warning(self, registry):
        """instance='auto' must not trigger the 'instance was not set' warning during init."""
        # "Loading account with the given token" warning fires regardless; check only for
        # the absence of the specific instance warning. Contrast with no-instance service.
        with self.assertLogs("qiskit_ibm_runtime", level="WARNING") as logs:
            QiskitRuntimeService(channel="ibm_quantum_platform", token="my_token")
        assert any("Instance was not set" in msg for msg in logs.output)

        with self.assertLogs("qiskit_ibm_runtime", level="WARNING") as logs:
            QiskitRuntimeService(channel="ibm_quantum_platform", token="my_token", instance="auto")
        assert not any("Instance was not set" in msg for msg in logs.output)

    @mock_responses
    def test_saved_account_instance_auto_sets_flag(self, registry):
        """A saved account with instance='auto' sets _instance_auto and clears the instance."""
        with temporary_account_config_file(
            channel="ibm_quantum_platform", token="my_token", instance="auto"
        ):
            service = QiskitRuntimeService()
        assert service._instance_auto
        assert service._account.instance is None
