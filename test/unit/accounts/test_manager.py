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

"""Tests for the account manager functionality."""

import os
import uuid
from unittest import skipIf

from qiskit_ibm_runtime.accounts import (
    Account,
    AccountAlreadyExistsError,
    AccountManager,
    AccountNotFoundError,
)
from qiskit_ibm_runtime.accounts.management import (
    _DEFAULT_ACCOUNT_NAME_IBM_CLOUD,
    _DEFAULT_ACCOUNT_NAME_IBM_QUANTUM_PLATFORM,
)
from qiskit_ibm_runtime.proxies import ProxyConfiguration
from qiskit_ibm_runtime.qiskit_runtime_service import QiskitRuntimeService
from test.account import custom_envs, no_envs, temporary_account_config_file
from test.decorators import mock_responses
from test.ibm_test_case import IBMTestCase

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

_TEST_IBM_CLOUD_ACCOUNT_DICT = _TEST_IBM_CLOUD_ACCOUNT.to_saved_format()
_TEST_IBM_QUANTUM_PLATFORM_ACCOUNT_DICT = _TEST_IBM_QUANTUM_PLATFORM_ACCOUNT.to_saved_format()
_TEST_FILENAME = "/tmp/temp_qiskit_account.json"

# An account on the legacy `ibm_quantum` channel, which is no longer listed.
_TEST_IBM_QUANTUM_CLASSIC_ACCOUNT_DICT = {
    "channel": "ibm_quantum",
    "url": "...",
    "token": "token-y",
    "instance": "...",
    "proxies": {
        "urls": {"https": "127.0.0.1"},
        "username_ntlm": "bla",
        "password_ntlm": "blub",
    },
    "verify": True,
    "private_endpoint": False,
}

# A named account, along with a default account for each of the channels.
_TEST_NAMED_AND_DEFAULT_ACCOUNTS = {
    "key1": _TEST_IBM_CLOUD_ACCOUNT_DICT,
    _DEFAULT_ACCOUNT_NAME_IBM_CLOUD: _TEST_IBM_CLOUD_ACCOUNT_DICT,
    _DEFAULT_ACCOUNT_NAME_IBM_QUANTUM_PLATFORM: _TEST_IBM_QUANTUM_PLATFORM_ACCOUNT_DICT,
}

# Named accounts, along with a default account for each of the channels.
_TEST_ACCOUNTS_WITH_DEFAULTS = {
    "key1": _TEST_IBM_CLOUD_ACCOUNT_DICT,
    "key2": _TEST_IBM_QUANTUM_PLATFORM_ACCOUNT_DICT,
    _DEFAULT_ACCOUNT_NAME_IBM_CLOUD: Account.create_account(
        channel="ibm_cloud", token="token-ibm-cloud", instance="crn:123"
    ).to_saved_format(),
    _DEFAULT_ACCOUNT_NAME_IBM_QUANTUM_PLATFORM: Account.create_account(
        channel="ibm_quantum_platform", token="token-ibm-cloud", instance="crn:123"
    ).to_saved_format(),
}


# NamedTemporaryFiles not supported in Windows
@skipIf(os.name == "nt", "Test not supported in Windows")
class TestAccountManager(IBMTestCase):
    """Tests for AccountManager class."""

    @temporary_account_config_file(contents={"conflict": _TEST_IBM_CLOUD_ACCOUNT_DICT})
    def test_save_without_overwrite_cloud(self):
        """Test to overwrite an existing account without setting overwrite=True."""
        with self.assertRaises(AccountAlreadyExistsError):
            AccountManager.save(
                name="conflict",
                token=_TEST_IBM_CLOUD_ACCOUNT.token,
                url=_TEST_IBM_CLOUD_ACCOUNT.url,
                instance=_TEST_IBM_CLOUD_ACCOUNT.instance,
                channel="ibm_cloud",
                overwrite=False,
            )
        AccountManager.save(
            filename=_TEST_FILENAME,
            name="conflict",
            token=_TEST_IBM_CLOUD_ACCOUNT.token,
            url=_TEST_IBM_CLOUD_ACCOUNT.url,
            instance=_TEST_IBM_CLOUD_ACCOUNT.instance,
            channel="ibm_cloud",
            overwrite=True,
        )
        with self.assertRaises(AccountAlreadyExistsError):
            AccountManager.save(
                filename=_TEST_FILENAME,
                name="conflict",
                token=_TEST_IBM_CLOUD_ACCOUNT.token,
                url=_TEST_IBM_CLOUD_ACCOUNT.url,
                instance=_TEST_IBM_CLOUD_ACCOUNT.instance,
                channel="ibm_cloud",
                overwrite=False,
            )

    @temporary_account_config_file(contents={"conflict": _TEST_IBM_QUANTUM_PLATFORM_ACCOUNT_DICT})
    def test_save_without_overwrite_iqp(self):
        """Test to overwrite an existing account without setting overwrite=True."""
        with self.assertRaises(AccountAlreadyExistsError):
            AccountManager.save(
                name="conflict",
                token=_TEST_IBM_QUANTUM_PLATFORM_ACCOUNT.token,
                url=_TEST_IBM_QUANTUM_PLATFORM_ACCOUNT.url,
                instance=_TEST_IBM_QUANTUM_PLATFORM_ACCOUNT.instance,
                channel="ibm_cloud",
                overwrite=False,
            )
        AccountManager.save(
            filename=_TEST_FILENAME,
            name="conflict",
            token=_TEST_IBM_QUANTUM_PLATFORM_ACCOUNT.token,
            url=_TEST_IBM_QUANTUM_PLATFORM_ACCOUNT.url,
            instance=_TEST_IBM_QUANTUM_PLATFORM_ACCOUNT.instance,
            channel="ibm_cloud",
            overwrite=True,
        )
        with self.assertRaises(AccountAlreadyExistsError):
            AccountManager.save(
                filename=_TEST_FILENAME,
                name="conflict",
                token=_TEST_IBM_QUANTUM_PLATFORM_ACCOUNT.token,
                url=_TEST_IBM_QUANTUM_PLATFORM_ACCOUNT.url,
                instance=_TEST_IBM_QUANTUM_PLATFORM_ACCOUNT.instance,
                channel="ibm_cloud",
                overwrite=False,
            )

    @temporary_account_config_file(contents={"conflict": _TEST_IBM_CLOUD_ACCOUNT_DICT})
    def test_get_none(self):
        """Test to get an account with an invalid name."""
        with self.assertRaises(AccountNotFoundError):
            AccountManager.get(name="bla")

    @temporary_account_config_file(contents={})
    @no_envs(["QISKIT_IBM_TOKEN"])
    def test_save_get(self):
        """Test save and get."""
        # Each tuple contains the
        # - account to save
        # - the name passed to AccountManager.save
        # - the name passed to AccountManager.get
        # Every case is run against the default account file and against a custom one.
        for file_name in (None, _TEST_FILENAME):
            for account, name_save, name_get in (
                # verify accounts can be saved and retrieved via custom names
                (_TEST_IBM_CLOUD_ACCOUNT, "acct-2", "acct-2"),
                (_TEST_IBM_QUANTUM_PLATFORM_ACCOUNT, "acct-3", "acct-3"),
                # verify default account name handling for ibm_quantum_platform accounts
                (
                    _TEST_IBM_QUANTUM_PLATFORM_ACCOUNT,
                    None,
                    _DEFAULT_ACCOUNT_NAME_IBM_QUANTUM_PLATFORM,
                ),
                (_TEST_IBM_QUANTUM_PLATFORM_ACCOUNT, None, None),
                # verify account override
                (_TEST_IBM_CLOUD_ACCOUNT, "acct", "acct"),
                (_TEST_IBM_QUANTUM_PLATFORM_ACCOUNT, "acct", "acct"),
            ):
                AccountManager.save(
                    token=account.token,
                    url=account.url,
                    instance=account.instance,
                    channel=account.channel,
                    proxies=account.proxies,
                    verify=account.verify,
                    filename=file_name,
                    name=name_save,
                    overwrite=True,
                )
                assert account == AccountManager.get(filename=file_name, name=name_get)

    @temporary_account_config_file(
        contents={
            "key1": _TEST_IBM_CLOUD_ACCOUNT_DICT,
            "key2": _TEST_IBM_QUANTUM_PLATFORM_ACCOUNT_DICT,
            "key3": _TEST_IBM_QUANTUM_CLASSIC_ACCOUNT_DICT,
        }
    )
    def test_list_skips_legacy_channel(self):
        """Test that listing accounts skips the ones on the legacy channel."""
        accounts = AccountManager.list()

        assert len(accounts) == 2
        assert accounts["key1"] == _TEST_IBM_CLOUD_ACCOUNT
        assert accounts["key2"] == _TEST_IBM_QUANTUM_PLATFORM_ACCOUNT

    @temporary_account_config_file(contents=_TEST_ACCOUNTS_WITH_DEFAULTS)
    def test_list_filtered(self):
        """Test listing accounts filtered by channel, by default, and by name."""
        accounts = list(AccountManager.list(channel="ibm_quantum_platform").keys())
        assert len(accounts) == 2
        assert accounts == ["key2", _DEFAULT_ACCOUNT_NAME_IBM_QUANTUM_PLATFORM]

        accounts = list(AccountManager.list(channel="ibm_quantum_platform", default=False).keys())
        assert len(accounts) == 1
        assert accounts == ["key2"]

        accounts = list(AccountManager.list(name="key1").keys())
        assert len(accounts) == 1
        assert accounts == ["key1"]

    @temporary_account_config_file(contents=_TEST_NAMED_AND_DEFAULT_ACCOUNTS)
    def test_delete_named_account(self):
        """Test deleting an account by name."""
        assert AccountManager.delete(name="key1")
        # Deleting the account a second time is a no-op.
        assert not AccountManager.delete(name="key1")

    @temporary_account_config_file(contents=_TEST_NAMED_AND_DEFAULT_ACCOUNTS)
    def test_delete_default_ibm_cloud_account(self):
        """Test deleting the default `ibm_cloud` account."""
        assert AccountManager.delete(channel="ibm_cloud")
        # Only the default `ibm_cloud` account is deleted.
        assert len(AccountManager.list()) == 2

    @temporary_account_config_file(contents=_TEST_NAMED_AND_DEFAULT_ACCOUNTS)
    def test_delete_default_ibm_quantum_platform_account(self):
        """Test deleting the default `ibm_quantum_platform` account."""
        assert AccountManager.delete()
        # Only the default `ibm_quantum_platform` account is deleted.
        assert len(AccountManager.list()) == 2

    def test_delete_filename(self):
        """Test delete accounts with filename parameter."""
        filename = _TEST_FILENAME
        name = "key1"
        channel = "ibm_quantum_platform"
        AccountManager.save(channel=channel, filename=filename, name=name, token="temp_token")
        assert AccountManager.delete(channel="ibm_quantum_platform", filename=filename, name=name)
        assert not AccountManager.delete(channel="ibm_quantum_platform", filename=filename, name=name)

        assert len(AccountManager.list(channel="ibm_quantum_platform", filename=filename)) == 0

    def test_account_with_filename(self):
        """Test saving an account to a given filename and retrieving it."""
        user_filename = _TEST_FILENAME
        account_name = "my_account"
        dummy_token = "dummy_token"
        AccountManager.save(
            channel="ibm_quantum_platform",
            filename=user_filename,
            name=account_name,
            overwrite=True,
            token=dummy_token,
        )
        account = AccountManager.get(
            channel="ibm_quantum_platform", filename=user_filename, name=account_name
        )
        assert account.token == dummy_token

    @mock_responses
    @temporary_account_config_file()
    def test_default_env_channel(self, registry):
        """Test that if QISKIT_IBM_CHANNEL is set in the environment, this channel will be used."""
        token = uuid.uuid4().hex
        # unset default_channel in the environment
        with temporary_account_config_file(token=token), no_envs("QISKIT_IBM_CHANNEL"):
            service = QiskitRuntimeService()
            assert service.channel == "ibm_quantum_platform"

        # set channel to default channel in the environment
        channel = "ibm_quantum_platform"
        with (
            temporary_account_config_file(channel=channel, token=token),
            custom_envs({"QISKIT_IBM_CHANNEL": channel}),
        ):
            service = QiskitRuntimeService()
            assert service.channel == channel

    def test_save_private_endpoint(self):
        """Test private endpoint parameter."""
        AccountManager.save(
            filename=_TEST_FILENAME,
            name=_DEFAULT_ACCOUNT_NAME_IBM_CLOUD,
            token=_TEST_IBM_CLOUD_ACCOUNT.token,
            instance=_TEST_IBM_CLOUD_ACCOUNT.instance,
            channel="ibm_cloud",
            overwrite=True,
            set_as_default=True,
            private_endpoint=True,
        )

        account = AccountManager.get(filename=_TEST_FILENAME)
        assert account.private_endpoint

    def test_save_default_account(self):
        """Test default_account defined in the qiskit-ibm.json file is used."""
        AccountManager.save(
            filename=_TEST_FILENAME,
            name=_DEFAULT_ACCOUNT_NAME_IBM_QUANTUM_PLATFORM,
            token=_TEST_IBM_QUANTUM_PLATFORM_ACCOUNT.token,
            url=_TEST_IBM_QUANTUM_PLATFORM_ACCOUNT.url,
            instance=_TEST_IBM_QUANTUM_PLATFORM_ACCOUNT.instance,
            channel="ibm_quantum_platform",
            overwrite=True,
            set_as_default=True,
        )

        with no_envs("QISKIT_IBM_CHANNEL"), no_envs("QISKIT_IBM_TOKEN"):
            account = AccountManager.get(filename=_TEST_FILENAME)
        assert account.channel == "ibm_quantum_platform"
        assert account.token == _TEST_IBM_CLOUD_ACCOUNT.token

    @mock_responses
    @temporary_account_config_file()
    def test_set_channel_precedence(self, registry):
        """Test the precedence of the various methods to set the account.

        account name > env_variables > channel parameter default account
               > default account > default account from default channel.
        """
        cloud_token = uuid.uuid4().hex
        preferred_token = uuid.uuid4().hex
        any_token = uuid.uuid4().hex
        channel_env = {"QISKIT_IBM_CHANNEL": "ibm_quantum_platform"}
        contents = {
            _DEFAULT_ACCOUNT_NAME_IBM_CLOUD: {
                "channel": "ibm_cloud",
                "token": cloud_token,
                "instance": _DEFAULT_CRN,
            },
            _DEFAULT_ACCOUNT_NAME_IBM_QUANTUM_PLATFORM: {
                "channel": "ibm_quantum_platform",
                "token": cloud_token,
                "instance": _DEFAULT_CRN,
            },
            "preferred-ibm-quantum": {
                "channel": "ibm_quantum_platform",
                "token": preferred_token,
                "is_default_account": True,
            },
            "any-quantum": {
                "channel": "ibm_quantum_platform",
                "token": any_token,
            },
        }

        # 'name' parameter
        with (
            temporary_account_config_file(contents=contents),
            custom_envs(channel_env),
            no_envs("QISKIT_IBM_TOKEN"),
        ):
            service = QiskitRuntimeService(name="any-quantum")
            assert service.channel == "ibm_quantum_platform"
            assert service._account.token == any_token

        # No name or channel params, no env vars, get the account specified as "is_default_account"
        with (
            temporary_account_config_file(contents=contents),
            no_envs("QISKIT_IBM_CHANNEL"),
            no_envs("QISKIT_IBM_TOKEN"),
        ):
            service = QiskitRuntimeService()
            assert service.channel == "ibm_quantum_platform"
            assert service._account.token == preferred_token

        # parameter 'channel' is specified, it overrides channel in env
        # account specified as "is_default_account"
        with (
            temporary_account_config_file(contents=contents),
            custom_envs(channel_env),
            no_envs("QISKIT_IBM_TOKEN"),
        ):
            service = QiskitRuntimeService(channel="ibm_quantum_platform")
            assert service.channel == "ibm_quantum_platform"
            assert service._account.token == preferred_token

        # account with default name for the channel
        contents["preferred-ibm-quantum"]["is_default_account"] = False
        with (
            temporary_account_config_file(contents=contents),
            custom_envs(channel_env),
            no_envs("QISKIT_IBM_TOKEN"),
        ):
            service = QiskitRuntimeService(channel="ibm_quantum_platform")
            assert service.channel == "ibm_quantum_platform"
            assert service._account.token == cloud_token

        # any account for this channel
        with (
            temporary_account_config_file(contents=contents),
            custom_envs(channel_env),
            no_envs("QISKIT_IBM_TOKEN"),
        ):
            service = QiskitRuntimeService(channel="ibm_quantum_platform")
            assert service.channel == "ibm_quantum_platform"
            assert service._account.token == cloud_token

        # no channel param, get account that is specified as "is_default_account"
        # for channel from env
        contents["preferred-ibm-quantum"]["is_default_account"] = True
        with (
            temporary_account_config_file(contents=contents),
            custom_envs(channel_env),
            no_envs("QISKIT_IBM_TOKEN"),
        ):
            service = QiskitRuntimeService()
            assert service.channel == "ibm_quantum_platform"
            assert service._account.token == preferred_token

        # no channel param, account with default name for the channel from env
        del contents["preferred-ibm-quantum"]["is_default_account"]
        contents["default-ibm-quantum"] = {
            "channel": "ibm_quantum_platform",
            "token": cloud_token,
        }
        channel_env = {"QISKIT_IBM_CHANNEL": "ibm_quantum_platform"}
        with (
            temporary_account_config_file(contents=contents),
            custom_envs(channel_env),
            no_envs("QISKIT_IBM_TOKEN"),
        ):
            service = QiskitRuntimeService()
            assert service.channel == "ibm_quantum_platform"
            assert service._account.token == cloud_token

        # no channel param, any account for the channel from env
        del contents["default-ibm-quantum"]
        with (
            temporary_account_config_file(contents=contents),
            custom_envs(channel_env),
            no_envs("QISKIT_IBM_TOKEN"),
        ):
            service = QiskitRuntimeService()
            assert service.channel == "ibm_quantum_platform"
            assert service._account.token == cloud_token
        # default channel
        with temporary_account_config_file(contents=contents), no_envs("QISKIT_IBM_CHANNEL"):
            service = QiskitRuntimeService()
            assert service.channel == "ibm_quantum_platform"

    def tearDown(self) -> None:
        """Test level tear down."""
        super().tearDown()
        if os.path.exists(_TEST_FILENAME):
            os.remove(_TEST_FILENAME)
