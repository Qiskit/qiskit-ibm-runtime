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

from __future__ import annotations

import copy
import logging
import os
import uuid
from typing import TYPE_CHECKING, Any, Literal

import pytest
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

if TYPE_CHECKING:
    from ...registries import BaseRegistry


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

MOCK_PROXY_CONFIG_DICT: dict[str, Any] = {
    "urls": {"https": "127.0.0.1", "username_ntlm": "", "password_ntlm": ""}
}

DUMMY_TOKEN = "123"
DUMMY_IBM_CLOUD_URL = "https://quantum.cloud.ibm.com"


def assert_preferences(prefs: dict, account: Account) -> None:
    """Assert that the preferences set in `prefs` match the ones of `account`."""
    if "proxies" in prefs:
        assert account.proxies == ProxyConfiguration(**prefs["proxies"])
    if "verify" in prefs:
        assert account.verify == prefs["verify"]
    if "instance" in prefs:
        assert account.instance == prefs["instance"]


class TestAccount:
    """Tests for Account class."""

    @pytest.mark.parametrize(
        "test_account", [_TEST_IBM_CLOUD_ACCOUNT, _TEST_IBM_QUANTUM_PLATFORM_ACCOUNT]
    )
    def test_skip_crn_resolution_for_crn(self, test_account: Account) -> None:
        """Test that CRN resolution is skipped if the instance value is already a CRN."""
        account = copy.deepcopy(test_account)
        account.resolve_crn()
        assert account.instance == test_account.instance

    def test_resolve_crn_proxied(self) -> None:
        """Account.resolve_crn() should go through proxies if specified."""
        account = Account.create_account(
            channel="ibm_quantum_platform",
            token="my_token",
            proxies=ProxyConfiguration(**MOCK_PROXY_CONFIG_DICT),
        )
        with pytest.raises(ProxyError):
            # Requests go through a proxy, which is not available in this test.
            account.resolve_crn()

    def test_invalid_channel(self) -> None:
        """Test invalid values for channel parameter."""
        with pytest.raises(InvalidAccountError) as err:
            invalid_channel: Any = "phantom"
            Account.create_account(
                channel=invalid_channel,
                token=DUMMY_TOKEN,
                url=DUMMY_IBM_CLOUD_URL,
            ).validate()
        assert "Invalid `channel` value." in str(err.value)

    @pytest.mark.parametrize("token", [1, None, ""])
    def test_invalid_token(self, token: Any) -> None:
        """Test invalid values for token parameter."""
        with pytest.raises(InvalidAccountError) as err:
            Account.create_account(
                channel="ibm_cloud",
                token=token,
                url=DUMMY_IBM_CLOUD_URL,
            ).validate()
        assert "Invalid `token` value." in str(err.value)

    def test_invalid_url(self) -> None:
        """Test invalid values for url parameter."""
        invalid_url: Any = 123

        with pytest.raises(InvalidAccountError) as err:
            Account.create_account(
                channel="ibm_cloud",
                token=DUMMY_TOKEN,
                url=invalid_url,
            ).validate()
        assert "Invalid `url` value." in str(err.value)

    def test_invalid_account_prefs(self) -> None:
        """Test invalid values for account preferences."""
        with pytest.raises(InvalidAccountError) as err:
            Account.create_account(
                channel="ibm_quantum_platform",
                token=DUMMY_TOKEN,
                url=DUMMY_IBM_CLOUD_URL,
                region="invalid-region",
            ).validate()
        assert "Invalid `region` value." in str(err.value)

        with pytest.raises(InvalidAccountError) as err:
            Account.create_account(
                channel="ibm_quantum_platform",
                token=DUMMY_TOKEN,
                url=DUMMY_IBM_CLOUD_URL,
                plans_preference="invalid-plans",  # type: ignore[arg-type]
            ).validate()
        assert "Invalid `plans_preference` value." in str(err.value)

        with pytest.raises(InvalidAccountError) as err:
            Account.create_account(
                channel="ibm_quantum_platform",
                token=DUMMY_TOKEN,
                url=DUMMY_IBM_CLOUD_URL,
                tags="invalid-tags",  # type: ignore[arg-type]
            ).validate()
        assert "Invalid `tags` value." in str(err.value)


# NamedTemporaryFiles not supported in Windows
@pytest.mark.skipif(os.name == "nt", reason="Test not supported in Windows")
class TestEnableAccount:
    """Tests for QiskitRuntimeService enable account."""

    def test_enable_account_by_name(self, registry: BaseRegistry) -> None:
        """Test initializing account by name."""
        name = "foo"
        token = uuid.uuid4().hex
        with temporary_account_config_file(name=name, token=token):
            service = QiskitRuntimeService(name=name)

        assert service._account
        assert service._account.token == token

    @pytest.mark.parametrize("channel", ["ibm_quantum_platform", "ibm_cloud"])
    def test_enable_account_by_channel(
        self, channel: Literal["ibm_quantum_platform", "ibm_cloud"], registry: BaseRegistry
    ) -> None:
        """Test initializing account by channel."""
        with no_envs(["QISKIT_IBM_TOKEN"]):
            token = uuid.uuid4().hex
            with temporary_account_config_file(channel=channel, token=token):
                service = QiskitRuntimeService(channel=channel)
            assert service._account
            assert service._account.token == token

    @pytest.mark.parametrize(
        "params",
        [
            {"token": uuid.uuid4().hex},
            {"token": uuid.uuid4().hex, "url": "https://foo.cloud.ibm.com"},
        ],
    )
    def test_enable_account_by_token_url(
        self, params: dict[str, Any], registry: BaseRegistry
    ) -> None:
        """Test initializing account by token."""
        with temporary_account_config_file(channel="ibm_quantum_platform", token=params["token"]):
            service = QiskitRuntimeService(**params)
            assert service._account

    def test_enable_account_by_url_error(self) -> None:
        """Test initializing account by url gives an error."""
        token = uuid.uuid4().hex
        with temporary_account_config_file(channel="ibm_quantum_platform", token=token):
            with pytest.raises(ValueError, match="not valid as a standalone parameter"):
                QiskitRuntimeService(url="some_url")

    @pytest.mark.parametrize(
        "params",
        [
            {"channel": "ibm_cloud"},
            {"token": "some_token"},
            {"url": "some_url"},
            {"channel": "ibm_cloud", "token": "some_token", "url": "some_url"},
        ],
    )
    def test_enable_account_by_name_and_other(
        self, params: dict[str, Any], registry: BaseRegistry, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test initializing account by name and other."""
        name = "foo"
        token = uuid.uuid4().hex
        with temporary_account_config_file(name=name, token=token):
            caplog.clear()
            with caplog.at_level(logging.WARNING, logger="qiskit_ibm_runtime"):
                service = QiskitRuntimeService(name=name, **params)

            assert service._account
            assert service._account.token == token
            assert "are ignored" in caplog.messages[0]

    @pytest.mark.parametrize("url", [None, "https://foo.cloud.ibm.com"])
    def test_enable_cloud_account_by_channel_token_url(
        self, url: str | None, registry: BaseRegistry
    ) -> None:
        """Test initializing cloud account by channel, token, url."""
        with no_envs(["QISKIT_IBM_TOKEN"]):
            token = uuid.uuid4().hex
            service = QiskitRuntimeService(channel="ibm_quantum_platform", token=token, url=url)
            assert service

    @pytest.mark.parametrize("channel", ["ibm_quantum_platform", "ibm_cloud"])
    def test_enable_account_by_channel_url(
        self,
        channel: Literal["ibm_quantum_platform", "ibm_cloud"],
        registry: BaseRegistry,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test initializing account by channel, token, url."""
        token = uuid.uuid4().hex
        with (
            temporary_account_config_file(channel=channel, token=token),
            no_envs(["QISKIT_IBM_TOKEN"]),
        ):
            caplog.clear()
            with caplog.at_level(logging.WARNING, logger="qiskit_ibm_runtime"):
                service = QiskitRuntimeService(channel=channel, url="some_url")

        assert service._account
        assert service._account.token == token
        expected = IBM_QUANTUM_PLATFORM_API_URL
        assert service._account.url == expected
        assert "url" in caplog.messages[0]

    @pytest.mark.parametrize("channel", ["ibm_quantum_platform", "ibm_cloud"])
    def test_enable_account_by_only_channel(
        self, channel: Literal["ibm_quantum_platform", "ibm_cloud"], registry: BaseRegistry
    ) -> None:
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

    def test_enable_account_both_channel(self, registry: BaseRegistry) -> None:
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

    @pytest.mark.parametrize("channel", ["ibm_quantum_platform", "ibm_cloud", None])
    def test_enable_account_by_env_channel(
        self, channel: Literal["ibm_quantum_platform", "ibm_cloud"] | None, registry: BaseRegistry
    ) -> None:
        """Test initializing account by environment variable and channel."""
        token = uuid.uuid4().hex
        url = "https://foo.cloud.ibm.com"
        envs = {
            "QISKIT_IBM_TOKEN": token,
            "QISKIT_IBM_URL": url,
            "QISKIT_IBM_INSTANCE": _DEFAULT_CRN,
        }
        with custom_envs(envs), no_envs(["QISKIT_IBM_CHANNEL"]):
            service = QiskitRuntimeService(channel=channel)

        assert service._account
        assert service._account.token == token
        assert service._account.url == url
        channel = channel or "ibm_quantum_platform"
        assert service._account.channel == channel

    @pytest.mark.parametrize("channel", ["ibm_quantum_platform", "ibm_cloud", None])
    def test_enable_account_only_env_variables(
        self, channel: Literal["ibm_quantum_platform", "ibm_cloud"] | None, registry: BaseRegistry
    ) -> None:
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

    @pytest.mark.parametrize(
        "params",
        [
            {"token": uuid.uuid4().hex},
            {"token": uuid.uuid4().hex, "url": "https://foo.cloud.ibm.com"},
        ],
    )
    def test_enable_account_by_env_token_url(
        self, params: dict[str, Any], registry: BaseRegistry
    ) -> None:
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

    def test_enable_account_bad_name(self) -> None:
        """Test initializing account by bad name."""
        name = "phantom"
        with temporary_account_config_file():
            with pytest.raises(AccountNotFoundError, match=f"Account with the name {name}"):
                _ = QiskitRuntimeService(name=name)

    def test_enable_account_bad_channel(self) -> None:
        """Test initializing account by bad name."""
        channel = "phantom"
        with temporary_account_config_file():
            with pytest.raises(ValueError, match="'channel' can only be"):
                QiskitRuntimeService(channel=channel)  # type: ignore[arg-type]

    @pytest.mark.parametrize(
        "params",
        [
            {"proxies": MOCK_PROXY_CONFIG_DICT},
            {"verify": False},
            {"instance": _DEFAULT_CRN},
            {"proxies": MOCK_PROXY_CONFIG_DICT, "verify": False, "instance": _DEFAULT_CRN},
        ],
    )
    def test_enable_account_by_name_pref(
        self, params: dict[str, Any], registry: BaseRegistry
    ) -> None:
        """Test initializing account by name and preferences."""
        name = "foo"
        with temporary_account_config_file(name=name, verify=True, proxies={}):
            service = QiskitRuntimeService(name=name, **params)
        assert service._account
        assert_preferences(params, service._account)

    @pytest.mark.parametrize("channel", ["ibm_quantum_platform", "ibm_cloud"])
    @pytest.mark.parametrize(
        "params",
        [
            {"proxies": MOCK_PROXY_CONFIG_DICT},
            {"verify": False},
            {"instance": _DEFAULT_CRN},
            {"proxies": MOCK_PROXY_CONFIG_DICT, "verify": False, "instance": _DEFAULT_CRN},
        ],
    )
    def test_enable_account_by_channel_pref(
        self,
        channel: Literal["ibm_quantum_platform", "ibm_cloud"],
        params: dict[str, Any],
        registry: BaseRegistry,
    ) -> None:
        """Test initializing account by channel and preferences."""
        with (
            temporary_account_config_file(channel=channel, verify=True, proxies={}),
            no_envs(["QISKIT_IBM_TOKEN"]),
        ):
            service = QiskitRuntimeService(channel=channel, **params)
            assert service._account
            assert_preferences(params, service._account)

    @pytest.mark.parametrize(
        "params",
        [
            {"proxies": MOCK_PROXY_CONFIG_DICT},
            {"verify": False},
            {"instance": _DEFAULT_CRN},
            {"proxies": MOCK_PROXY_CONFIG_DICT, "verify": False, "instance": _DEFAULT_CRN},
        ],
    )
    def test_enable_account_by_env_pref(
        self, params: dict[str, Any], registry: BaseRegistry
    ) -> None:
        """Test initializing account by environment variable and preferences."""
        token = uuid.uuid4().hex
        url = "https://foo.cloud.ibm.com"
        envs = {
            "QISKIT_IBM_TOKEN": token,
            "QISKIT_IBM_URL": url,
            "QISKIT_IBM_INSTANCE": _DEFAULT_CRN,
        }
        with custom_envs(envs), no_envs(["QISKIT_IBM_CHANNEL"]):
            service = QiskitRuntimeService(**params)

        assert service._account
        assert_preferences(params, service._account)

    def test_enable_account_by_name_input_instance(self, registry: BaseRegistry) -> None:
        """Test initializing account by name and input instance."""
        name = "foo"
        instance = _DEFAULT_CRN
        with temporary_account_config_file(name=name, instance="stored-instance"):
            service = QiskitRuntimeService(name=name, instance=instance)
        assert service._account
        assert service._account.instance == instance

    def test_enable_account_by_channel_input_instance(self, registry: BaseRegistry) -> None:
        """Test initializing account by channel and input instance."""
        instance = _DEFAULT_CRN
        with temporary_account_config_file(channel="ibm_quantum_platform", instance="bla"):
            service = QiskitRuntimeService(channel="ibm_quantum_platform", instance=instance)
        assert service._account
        assert service._account.instance == instance

    def test_enable_account_by_env_input_instance(self, registry: BaseRegistry) -> None:
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

    def test_instance_filter_tags(self, registry: BaseRegistry) -> None:
        """Test initializing account by channel and input instance."""
        registry.instances["a"].tags = ["services"]

        tags = ["services"]
        with temporary_account_config_file(channel="ibm_quantum_platform"):
            service = QiskitRuntimeService(channel="ibm_quantum_platform", tags=tags)
            assert service._account
            for inst in service._backend_instance_groups:
                assert inst["tags"] == tags

            with pytest.raises(IBMInputValueError, match="No matching instances"):
                service = QiskitRuntimeService(
                    channel="ibm_quantum_platform", tags=["invalid_tags"]
                )

    def test_wrong_instance(self, registry: BaseRegistry) -> None:
        """Test an instance from a different account."""
        instance = "wrong_instance"
        with temporary_account_config_file(channel="ibm_quantum_platform"):
            with pytest.raises(IBMInputValueError, match="not a valid instance name"):
                QiskitRuntimeService(channel="ibm_quantum_platform", instance=instance)

    def test_instance_auto_flag_set(self, registry: BaseRegistry) -> None:
        """instance='auto' sets _instance_auto and leaves account.instance as None."""
        service = QiskitRuntimeService(
            channel="ibm_quantum_platform", token="my_token", instance="auto"
        )
        assert service._instance_auto
        assert service._account.instance is None

    def test_instance_auto_suppresses_init_warning(
        self, registry: BaseRegistry, caplog: pytest.LogCaptureFixture
    ) -> None:
        """instance='auto' must not trigger the 'instance was not set' warning during init."""
        # "Loading account with the given token" warning fires regardless; check only for
        # the absence of the specific instance warning. Contrast with no-instance service.
        caplog.clear()
        with caplog.at_level(logging.WARNING, logger="qiskit_ibm_runtime"):
            QiskitRuntimeService(channel="ibm_quantum_platform", token="my_token")
        assert any("Instance was not set" in msg for msg in caplog.messages)

        caplog.clear()
        with caplog.at_level(logging.WARNING, logger="qiskit_ibm_runtime"):
            QiskitRuntimeService(channel="ibm_quantum_platform", token="my_token", instance="auto")
        assert not any("Instance was not set" in msg for msg in caplog.messages)

    def test_saved_account_instance_auto_sets_flag(self, registry: BaseRegistry) -> None:
        """A saved account with instance='auto' sets _instance_auto and clears the instance."""
        with temporary_account_config_file(
            channel="ibm_quantum_platform", token="my_token", instance="auto"
        ):
            service = QiskitRuntimeService()
        assert service._instance_auto
        assert service._account.instance is None
