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

"""Tests for the account functions."""
import copy
import json
import logging
import os
import uuid
from typing import Any
from unittest import skipIf

from qiskit_ibm_runtime.accounts import (
    AccountManager,
    Account,
    AccountAlreadyExistsError,
    AccountNotFoundError,
    InvalidAccountError,
)
from qiskit_ibm_runtime.accounts.account import IBM_CLOUD_API_URL, IBM_QUANTUM_API_URL
from qiskit_ibm_runtime.accounts.management import (
    _DEFAULT_ACCOUNT_NAME_LEGACY,
    _DEFAULT_ACCOUNT_NAME_CLOUD,
    _DEFAULT_ACCOUNT_NAME_IBM_QUANTUM,
    _DEFAULT_ACCOUNT_NAME_IBM_CLOUD,
)
from qiskit_ibm_runtime.proxies import ProxyConfiguration
from .mock.fake_runtime_service import FakeRuntimeService
from ..ibm_test_case import IBMTestCase
from ..account import (
    get_account_config_contents,
    temporary_account_config_file,
    custom_qiskitrc,
    no_envs,
    custom_envs,
)

_TEST_IBM_QUANTUM_ACCOUNT = Account(
    channel="ibm_quantum",
    token="token-x",
    url="https://auth.quantum-computing.ibm.com/api",
    instance="ibm-q/open/main",
)

_TEST_IBM_CLOUD_ACCOUNT = Account(
    channel="ibm_cloud",
    token="token-y",
    url="https://cloud.ibm.com",
    instance="crn:v1:bluemix:public:quantum-computing:us-east:a/...::",
    proxies=ProxyConfiguration(
        username_ntlm="bla", password_ntlm="blub", urls={"https": "127.0.0.1"}
    ),
)

_TEST_LEGACY_ACCOUNT = {
    "auth": "legacy",
    "token": "token-x",
    "url": "https://auth.quantum-computing.ibm.com/api",
    "instance": "ibm-q/open/main",
}

_TEST_CLOUD_ACCOUNT = {
    "auth": "cloud",
    "token": "token-y",
    "url": "https://cloud.ibm.com",
    "instance": "crn:v1:bluemix:public:quantum-computing:us-east:a/...::",
    "proxies": {
        "username_ntlm": "bla",
        "password_ntlm": "blub",
        "urls": {"https": "127.0.0.1"},
    },
}

_TEST_FILENAME = "/tmp/temp_qiskit_account.json"


class TestAccount(IBMTestCase):
    """Tests for Account class."""

    dummy_token = "123"
    dummy_ibm_cloud_url = "https://us-east.quantum-computing.cloud.ibm.com"
    dummy_ibm_quantum_url = "https://auth.quantum-computing.ibm.com/api"

    def test_skip_crn_resolution_for_crn(self):
        """Test that CRN resolution is skipped if the instance value is already a CRN."""
        account = copy.deepcopy(_TEST_IBM_CLOUD_ACCOUNT)
        account.resolve_crn()
        self.assertEqual(account.instance, _TEST_IBM_CLOUD_ACCOUNT.instance)

    def test_invalid_channel(self):
        """Test invalid values for channel parameter."""

        with self.assertRaises(InvalidAccountError) as err:
            invalid_channel: Any = "phantom"
            Account(
                channel=invalid_channel,
                token=self.dummy_token,
                url=self.dummy_ibm_cloud_url,
            ).validate()
        self.assertIn("Invalid `channel` value.", str(err.exception))

    def test_invalid_token(self):
        """Test invalid values for token parameter."""

        invalid_tokens = [1, None, ""]
        for token in invalid_tokens:
            with self.subTest(token=token):
                with self.assertRaises(InvalidAccountError) as err:
                    Account(
                        channel="ibm_cloud",
                        token=token,
                        url=self.dummy_ibm_cloud_url,
                    ).validate()
                self.assertIn("Invalid `token` value.", str(err.exception))

    def test_invalid_url(self):
        """Test invalid values for url parameter."""

        subtests = [
            {"channel": "ibm_cloud", "url": 123},
        ]
        for params in subtests:
            with self.subTest(params=params):
                with self.assertRaises(InvalidAccountError) as err:
                    Account(**params, token=self.dummy_token).validate()
                self.assertIn("Invalid `url` value.", str(err.exception))

    def test_invalid_instance(self):
        """Test invalid values for instance parameter."""

        subtests = [
            {"channel": "ibm_cloud", "instance": ""},
            {"channel": "ibm_cloud"},
            {"channel": "ibm_quantum", "instance": "no-hgp-format"},
        ]
        for params in subtests:
            with self.subTest(params=params):
                with self.assertRaises(InvalidAccountError) as err:
                    Account(
                        **params, token=self.dummy_token, url=self.dummy_ibm_cloud_url
                    ).validate()
                self.assertIn("Invalid `instance` value.", str(err.exception))

    def test_invalid_proxy_config(self):
        """Test invalid values for proxy configuration."""

        subtests = [
            {
                "proxies": ProxyConfiguration(**{"username_ntlm": "user-only"}),
            },
            {
                "proxies": ProxyConfiguration(**{"password_ntlm": "password-only"}),
            },
            {
                "proxies": ProxyConfiguration(**{"urls": ""}),
            },
        ]
        for params in subtests:
            with self.subTest(params=params):
                with self.assertRaises(ValueError) as err:
                    Account(
                        **params,
                        channel="ibm_quantum",
                        token=self.dummy_token,
                        url=self.dummy_ibm_cloud_url,
                    ).validate()
                self.assertIn("Invalid proxy configuration", str(err.exception))


# NamedTemporaryFiles not supported in Windows
@skipIf(os.name == "nt", "Test not supported in Windows")
class TestAccountManager(IBMTestCase):
    """Tests for AccountManager class."""

    @temporary_account_config_file(
        contents={"conflict": _TEST_IBM_CLOUD_ACCOUNT.to_saved_format()}
    )
    def test_save_without_overwrite(self):
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

    # TODO remove test when removing auth parameter
    @temporary_account_config_file(
        contents={_DEFAULT_ACCOUNT_NAME_CLOUD: _TEST_CLOUD_ACCOUNT}
    )
    @no_envs(["QISKIT_IBM_TOKEN"])
    def test_save_channel_ibm_cloud_over_auth_cloud_without_overwrite(self):
        """Test to overwrite an existing auth "cloud" account with channel "ibm_cloud"
        and without setting overwrite=True."""
        with self.assertRaises(AccountAlreadyExistsError):
            AccountManager.save(
                token=_TEST_IBM_CLOUD_ACCOUNT.token,
                url=_TEST_IBM_CLOUD_ACCOUNT.url,
                instance=_TEST_IBM_CLOUD_ACCOUNT.instance,
                channel="ibm_cloud",
                name=None,
                overwrite=False,
            )

    # TODO remove test when removing auth parameter
    @temporary_account_config_file(
        contents={_DEFAULT_ACCOUNT_NAME_LEGACY: _TEST_LEGACY_ACCOUNT}
    )
    @no_envs(["QISKIT_IBM_TOKEN"])
    def test_save_channel_ibm_quantum_over_auth_legacy_without_overwrite(self):
        """Test to overwrite an existing auth "legacy" account with channel "ibm_quantum"
        and without setting overwrite=True."""
        with self.assertRaises(AccountAlreadyExistsError):
            AccountManager.save(
                token=_TEST_IBM_QUANTUM_ACCOUNT.token,
                url=_TEST_IBM_QUANTUM_ACCOUNT.url,
                instance=_TEST_IBM_QUANTUM_ACCOUNT.instance,
                channel="ibm_quantum",
                name=None,
                overwrite=False,
            )

    # TODO remove test when removing auth parameter
    @temporary_account_config_file(
        contents={_DEFAULT_ACCOUNT_NAME_LEGACY: _TEST_LEGACY_ACCOUNT}
    )
    @no_envs(["QISKIT_IBM_TOKEN"])
    def test_save_channel_ibm_quantum_over_auth_legacy_with_overwrite(self):
        """Test to overwrite an existing auth "legacy" account with channel "ibm_quantum"
        and with setting overwrite=True."""
        AccountManager.save(
            token=_TEST_IBM_QUANTUM_ACCOUNT.token,
            url=_TEST_IBM_QUANTUM_ACCOUNT.url,
            instance=_TEST_IBM_QUANTUM_ACCOUNT.instance,
            channel="ibm_quantum",
            name=None,
            overwrite=True,
        )
        self.assertEqual(
            _TEST_IBM_QUANTUM_ACCOUNT, AccountManager.get(channel="ibm_quantum")
        )

    # TODO remove test when removing auth parameter
    @temporary_account_config_file(
        contents={_DEFAULT_ACCOUNT_NAME_CLOUD: _TEST_CLOUD_ACCOUNT}
    )
    @no_envs(["QISKIT_IBM_TOKEN"])
    def test_save_channel_ibm_cloud_over_auth_cloud_with_overwrite(self):
        """Test to overwrite an existing auth "cloud" account with channel "ibm_cloud"
        and with setting overwrite=True."""
        AccountManager.save(
            token=_TEST_IBM_CLOUD_ACCOUNT.token,
            url=_TEST_IBM_CLOUD_ACCOUNT.url,
            instance=_TEST_IBM_CLOUD_ACCOUNT.instance,
            channel="ibm_cloud",
            proxies=_TEST_IBM_CLOUD_ACCOUNT.proxies,
            name=None,
            overwrite=True,
        )
        self.assertEqual(
            _TEST_IBM_CLOUD_ACCOUNT, AccountManager.get(channel="ibm_cloud")
        )

    # TODO remove test when removing auth parameter
    @temporary_account_config_file(contents={"personal-account": _TEST_CLOUD_ACCOUNT})
    def test_save_channel_ibm_cloud_with_name_over_auth_cloud_with_overwrite(self):
        """Test to overwrite an existing named auth "cloud" account with channel "ibm_cloud"
        and with setting overwrite=True."""
        AccountManager.save(
            token=_TEST_IBM_CLOUD_ACCOUNT.token,
            url=_TEST_IBM_CLOUD_ACCOUNT.url,
            instance=_TEST_IBM_CLOUD_ACCOUNT.instance,
            channel="ibm_cloud",
            proxies=_TEST_IBM_CLOUD_ACCOUNT.proxies,
            name="personal-account",
            overwrite=True,
        )
        self.assertEqual(
            _TEST_IBM_CLOUD_ACCOUNT, AccountManager.get(name="personal-account")
        )

    # TODO remove test when removing auth parameter
    @temporary_account_config_file(contents={"personal-account": _TEST_CLOUD_ACCOUNT})
    def test_save_channel_ibm_cloud_with_name_over_auth_cloud_without_overwrite(self):
        """Test to overwrite an existing named auth "cloud" account with channel "ibm_cloud"
        and without setting overwrite=True."""
        with self.assertRaises(AccountAlreadyExistsError):
            AccountManager.save(
                token=_TEST_IBM_CLOUD_ACCOUNT.token,
                url=_TEST_IBM_CLOUD_ACCOUNT.url,
                instance=_TEST_IBM_CLOUD_ACCOUNT.instance,
                channel="ibm_cloud",
                proxies=_TEST_IBM_CLOUD_ACCOUNT.proxies,
                name="personal-account",
                overwrite=False,
            )

    # TODO remove test when removing auth parameter
    @temporary_account_config_file(contents={"personal-account": _TEST_LEGACY_ACCOUNT})
    def test_save_channel_ibm_quantum_with_name_over_auth_legacy_with_overwrite(self):
        """Test to overwrite an existing named auth "legacy" account with channel "ibm_quantum"
        and with setting overwrite=True."""
        AccountManager.save(
            token=_TEST_IBM_QUANTUM_ACCOUNT.token,
            url=_TEST_IBM_QUANTUM_ACCOUNT.url,
            instance=_TEST_IBM_QUANTUM_ACCOUNT.instance,
            channel="ibm_quantum",
            proxies=_TEST_IBM_QUANTUM_ACCOUNT.proxies,
            name="personal-account",
            overwrite=True,
        )
        self.assertEqual(
            _TEST_IBM_QUANTUM_ACCOUNT, AccountManager.get(name="personal-account")
        )

    # TODO remove test when removing auth parameter
    @temporary_account_config_file(contents={"personal-account": _TEST_LEGACY_ACCOUNT})
    def test_save_channel_ibm_quantum_with_name_over_auth_legacy_without_overwrite(
        self,
    ):
        """Test to overwrite an existing named auth "legacy" account with channel "ibm_quantum"
        and without setting overwrite=True."""
        with self.assertRaises(AccountAlreadyExistsError):
            AccountManager.save(
                token=_TEST_IBM_QUANTUM_ACCOUNT.token,
                url=_TEST_IBM_QUANTUM_ACCOUNT.url,
                instance=_TEST_IBM_QUANTUM_ACCOUNT.instance,
                channel="ibm_quantum",
                proxies=_TEST_IBM_QUANTUM_ACCOUNT.proxies,
                name="personal-account",
                overwrite=False,
            )

    @temporary_account_config_file(
        contents={"conflict": _TEST_IBM_CLOUD_ACCOUNT.to_saved_format()}
    )
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
        user_filename = _TEST_FILENAME
        sub_tests = [
            # verify accounts can be saved and retrieved via custom names
            (_TEST_IBM_QUANTUM_ACCOUNT, None, "acct-1", "acct-1"),
            (_TEST_IBM_CLOUD_ACCOUNT, None, "acct-2", "acct-2"),
            # verify default account name handling for ibm_cloud accounts
            (_TEST_IBM_CLOUD_ACCOUNT, None, None, _DEFAULT_ACCOUNT_NAME_IBM_CLOUD),
            (_TEST_IBM_CLOUD_ACCOUNT, None, None, None),
            # verify default account name handling for ibm_quantum accounts
            (
                _TEST_IBM_QUANTUM_ACCOUNT,
                None,
                None,
                _DEFAULT_ACCOUNT_NAME_IBM_QUANTUM,
            ),
            # verify account override
            (_TEST_IBM_QUANTUM_ACCOUNT, None, "acct", "acct"),
            (_TEST_IBM_CLOUD_ACCOUNT, None, "acct", "acct"),
            # same as above with filename
            (_TEST_IBM_QUANTUM_ACCOUNT, user_filename, "acct-1", "acct-1"),
            (_TEST_IBM_CLOUD_ACCOUNT, user_filename, "acct-2", "acct-2"),
            # verify default account name handling for ibm_cloud accounts
            (
                _TEST_IBM_CLOUD_ACCOUNT,
                user_filename,
                None,
                _DEFAULT_ACCOUNT_NAME_IBM_CLOUD,
            ),
            (_TEST_IBM_CLOUD_ACCOUNT, user_filename, None, None),
            # verify default account name handling for ibm_quantum accounts
            (
                _TEST_IBM_QUANTUM_ACCOUNT,
                user_filename,
                None,
                _DEFAULT_ACCOUNT_NAME_IBM_QUANTUM,
            ),
            # verify account override
            (_TEST_IBM_QUANTUM_ACCOUNT, user_filename, "acct", "acct"),
            (_TEST_IBM_CLOUD_ACCOUNT, user_filename, "acct", "acct"),
        ]
        for account, file_name, name_save, name_get in sub_tests:
            with self.subTest(
                f"for account type '{account.channel}' "
                f"using `save(name={name_save})` and `get(name={name_get})`"
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
                self.assertEqual(
                    account, AccountManager.get(filename=file_name, name=name_get)
                )

    @temporary_account_config_file(
        contents=json.dumps(
            {
                "ibm_cloud": _TEST_IBM_CLOUD_ACCOUNT.to_saved_format(),
                "ibm_quantum": _TEST_IBM_QUANTUM_ACCOUNT.to_saved_format(),
            }
        )
    )
    def test_list(self):
        """Test list."""

        with temporary_account_config_file(
            contents={
                "key1": _TEST_IBM_CLOUD_ACCOUNT.to_saved_format(),
                "key2": _TEST_IBM_QUANTUM_ACCOUNT.to_saved_format(),
            }
        ), self.subTest("non-empty list of accounts"):
            accounts = AccountManager.list()

            self.assertEqual(len(accounts), 2)
            self.assertEqual(accounts["key1"], _TEST_IBM_CLOUD_ACCOUNT)
            self.assertTrue(accounts["key2"], _TEST_IBM_QUANTUM_ACCOUNT)

        with temporary_account_config_file(
            contents={
                _DEFAULT_ACCOUNT_NAME_CLOUD: _TEST_CLOUD_ACCOUNT,
                _DEFAULT_ACCOUNT_NAME_LEGACY: _TEST_CLOUD_ACCOUNT,
            }
        ), self.subTest("non-empty list of auth accounts"):
            accounts = AccountManager.list()

            self.assertEqual(len(accounts), 2)
            self.assertEqual(
                accounts[_DEFAULT_ACCOUNT_NAME_IBM_CLOUD], _TEST_IBM_CLOUD_ACCOUNT
            )
            self.assertTrue(
                accounts[_DEFAULT_ACCOUNT_NAME_IBM_QUANTUM], _TEST_IBM_QUANTUM_ACCOUNT
            )

        with temporary_account_config_file(contents={}), self.subTest(
            "empty list of accounts"
        ):
            self.assertEqual(len(AccountManager.list()), 0)

        with temporary_account_config_file(
            contents={
                "key1": _TEST_IBM_CLOUD_ACCOUNT.to_saved_format(),
                "key2": _TEST_IBM_QUANTUM_ACCOUNT.to_saved_format(),
                _DEFAULT_ACCOUNT_NAME_IBM_CLOUD: Account(
                    "ibm_cloud", "token-ibm-cloud", instance="crn:123"
                ).to_saved_format(),
                _DEFAULT_ACCOUNT_NAME_IBM_QUANTUM: Account(
                    "ibm_quantum", "token-ibm-quantum"
                ).to_saved_format(),
            }
        ), self.subTest("filtered list of accounts"):
            accounts = list(AccountManager.list(channel="ibm_cloud").keys())
            self.assertEqual(len(accounts), 2)
            self.assertListEqual(accounts, ["key1", _DEFAULT_ACCOUNT_NAME_IBM_CLOUD])

            accounts = list(AccountManager.list(channel="ibm_quantum").keys())
            self.assertEqual(len(accounts), 2)
            self.assertListEqual(accounts, ["key2", _DEFAULT_ACCOUNT_NAME_IBM_QUANTUM])

            accounts = list(
                AccountManager.list(channel="ibm_cloud", default=True).keys()
            )
            self.assertEqual(len(accounts), 1)
            self.assertListEqual(accounts, [_DEFAULT_ACCOUNT_NAME_IBM_CLOUD])

            accounts = list(
                AccountManager.list(channel="ibm_cloud", default=False).keys()
            )
            self.assertEqual(len(accounts), 1)
            self.assertListEqual(accounts, ["key1"])

            accounts = list(AccountManager.list(name="key1").keys())
            self.assertEqual(len(accounts), 1)
            self.assertListEqual(accounts, ["key1"])

        # TODO remove test when removing auth parameter
        with temporary_account_config_file(
            contents={
                "key1": _TEST_CLOUD_ACCOUNT,
                "key2": _TEST_LEGACY_ACCOUNT,
                _DEFAULT_ACCOUNT_NAME_CLOUD: _TEST_CLOUD_ACCOUNT,
                _DEFAULT_ACCOUNT_NAME_LEGACY: _TEST_LEGACY_ACCOUNT,
            }
        ), self.subTest("filtered list of auth accounts"):
            accounts = list(AccountManager.list(channel="ibm_cloud").keys())
            self.assertEqual(len(accounts), 2)
            self.assertListEqual(accounts, [_DEFAULT_ACCOUNT_NAME_IBM_CLOUD, "key1"])

            accounts = list(AccountManager.list(channel="ibm_quantum").keys())
            self.assertEqual(len(accounts), 2)
            self.assertListEqual(accounts, [_DEFAULT_ACCOUNT_NAME_IBM_QUANTUM, "key2"])

            accounts = list(
                AccountManager.list(channel="ibm_cloud", default=True).keys()
            )
            self.assertEqual(len(accounts), 1)
            self.assertListEqual(accounts, [_DEFAULT_ACCOUNT_NAME_IBM_CLOUD])

            accounts = list(
                AccountManager.list(channel="ibm_cloud", default=False).keys()
            )
            self.assertEqual(len(accounts), 1)
            self.assertListEqual(accounts, ["key1"])

            accounts = list(AccountManager.list(name="key1").keys())
            self.assertEqual(len(accounts), 1)
            self.assertListEqual(accounts, ["key1"])

    @temporary_account_config_file(
        contents={
            "key1": _TEST_IBM_CLOUD_ACCOUNT.to_saved_format(),
            _DEFAULT_ACCOUNT_NAME_IBM_QUANTUM: _TEST_IBM_QUANTUM_ACCOUNT.to_saved_format(),
            _DEFAULT_ACCOUNT_NAME_IBM_CLOUD: _TEST_IBM_CLOUD_ACCOUNT.to_saved_format(),
        }
    )
    def test_delete(self):
        """Test delete."""

        with self.subTest("delete named account"):
            self.assertTrue(AccountManager.delete(name="key1"))
            self.assertFalse(AccountManager.delete(name="key1"))

        with self.subTest("delete default ibm_quantum account"):
            self.assertTrue(AccountManager.delete(channel="ibm_quantum"))

        with self.subTest("delete default ibm_cloud account"):
            self.assertTrue(AccountManager.delete())

            self.assertTrue(len(AccountManager.list()) == 0)

    @temporary_account_config_file(
        contents={
            "key1": _TEST_CLOUD_ACCOUNT,
            _DEFAULT_ACCOUNT_NAME_LEGACY: _TEST_LEGACY_ACCOUNT,
            _DEFAULT_ACCOUNT_NAME_CLOUD: _TEST_CLOUD_ACCOUNT,
        }
    )
    def test_delete_auth(self):
        """Test delete accounts already saved using auth."""

        with self.subTest("delete named account"):
            self.assertTrue(AccountManager.delete(name="key1"))
            self.assertFalse(AccountManager.delete(name="key1"))

        with self.subTest("delete default auth='legacy' account using channel"):
            self.assertTrue(AccountManager.delete(channel="ibm_quantum"))

        with self.subTest("delete default auth='cloud' account using channel"):
            self.assertTrue(AccountManager.delete())

        self.assertTrue(len(AccountManager.list()) == 0)

    def test_delete_filename(self):
        """Test delete accounts with filename parameter."""

        filename = "~/account_to_delete.json"
        name = "key1"
        channel = "ibm_quantum"
        AccountManager.save(
            channel=channel, filename=filename, name=name, token="temp_token"
        )
        self.assertTrue(
            AccountManager.delete(channel="ibm_quantum", filename=filename, name=name)
        )
        self.assertFalse(
            AccountManager.delete(channel="ibm_quantum", filename=filename, name=name)
        )

        self.assertTrue(
            len(AccountManager.list(channel="ibm_quantum", filename=filename)) == 0
        )

    def test_account_with_filename(self):
        """Test saving an account to a given filename and retrieving it."""
        user_filename = _TEST_FILENAME
        account_name = "my_account"
        dummy_token = "dummy_token"
        AccountManager.save(
            channel="ibm_quantum",
            filename=user_filename,
            name=account_name,
            overwrite=True,
            token=dummy_token,
        )
        account = AccountManager.get(
            channel="ibm_quantum", filename=user_filename, name=account_name
        )
        self.assertEqual(account.token, dummy_token)

    def tearDown(self) -> None:
        """Test level tear down."""
        super().tearDown()
        if os.path.exists(_TEST_FILENAME):
            os.remove(_TEST_FILENAME)


MOCK_PROXY_CONFIG_DICT = {
    "urls": {"https": "127.0.0.1", "username_ntlm": "", "password_ntlm": ""}
}
# NamedTemporaryFiles not supported in Windows
@skipIf(os.name == "nt", "Test not supported in Windows")
class TestEnableAccount(IBMTestCase):
    """Tests for QiskitRuntimeService enable account."""

    def test_enable_account_by_name(self):
        """Test initializing account by name."""
        name = "foo"
        token = uuid.uuid4().hex
        with temporary_account_config_file(name=name, token=token):
            service = FakeRuntimeService(name=name)

        self.assertTrue(service._account)
        self.assertEqual(service._account.token, token)

    def test_enable_account_by_channel(self):
        """Test initializing account by channel."""
        for channel in ["ibm_cloud", "ibm_quantum"]:
            with self.subTest(channel=channel), no_envs(["QISKIT_IBM_TOKEN"]):
                token = uuid.uuid4().hex
                with temporary_account_config_file(channel=channel, token=token):
                    service = FakeRuntimeService(channel=channel)
                self.assertTrue(service._account)
                self.assertEqual(service._account.token, token)

    def test_enable_account_by_token_url(self):
        """Test initializing account by token or url."""
        token = uuid.uuid4().hex
        subtests = [
            {"token": token},
            {"url": "some_url"},
            {"token": token, "url": "some_url"},
        ]
        for param in subtests:
            with self.subTest(param=param):
                with self.assertRaises(ValueError):
                    _ = FakeRuntimeService(**param)

    def test_enable_account_by_name_and_other(self):
        """Test initializing account by name and other."""
        subtests = [
            {"channel": "ibm_cloud"},
            {"token": "some_token"},
            {"url": "some_url"},
            {"channel": "ibm_cloud", "token": "some_token", "url": "some_url"},
        ]

        name = "foo"
        token = uuid.uuid4().hex
        for param in subtests:
            with self.subTest(param=param), temporary_account_config_file(
                name=name, token=token
            ):
                with self.assertLogs("qiskit_ibm_runtime", logging.WARNING) as logged:
                    service = FakeRuntimeService(name=name, **param)

                self.assertTrue(service._account)
                self.assertEqual(service._account.token, token)
                self.assertIn("are ignored", logged.output[0])

    def test_enable_cloud_account_by_channel_token_url(self):
        """Test initializing cloud account by channel, token, url."""
        # Enable account will fail due to missing CRN.
        urls = [None, "some_url"]
        for url in urls:
            with self.subTest(url=url), no_envs(["QISKIT_IBM_TOKEN"]):
                token = uuid.uuid4().hex
                with self.assertRaises(InvalidAccountError) as err:
                    _ = FakeRuntimeService(channel="ibm_cloud", token=token, url=url)
                self.assertIn("instance", str(err.exception))

    def test_enable_ibm_quantum_account_by_channel_token_url(self):
        """Test initializing ibm_quantum account by channel, token, url."""
        urls = [(None, IBM_QUANTUM_API_URL), ("some_url", "some_url")]
        for url, expected in urls:
            with self.subTest(url=url), no_envs(["QISKIT_IBM_TOKEN"]):
                token = uuid.uuid4().hex
                service = FakeRuntimeService(
                    channel="ibm_quantum", token=token, url=url
                )
                self.assertTrue(service._account)
                self.assertEqual(service._account.token, token)
                self.assertEqual(service._account.url, expected)

    def test_enable_account_by_channel_url(self):
        """Test initializing ibm_quantum account by channel, token, url."""
        subtests = ["ibm_cloud", "ibm_quantum"]
        for channel in subtests:
            with self.subTest(channel=channel):
                token = uuid.uuid4().hex
                with temporary_account_config_file(
                    channel=channel, token=token
                ), no_envs(["QISKIT_IBM_TOKEN"]):
                    with self.assertLogs(
                        "qiskit_ibm_runtime", logging.WARNING
                    ) as logged:
                        service = FakeRuntimeService(channel=channel, url="some_url")

                self.assertTrue(service._account)
                self.assertEqual(service._account.token, token)
                expected = (
                    IBM_CLOUD_API_URL if channel == "ibm_cloud" else IBM_QUANTUM_API_URL
                )
                self.assertEqual(service._account.url, expected)
                self.assertIn("url", logged.output[0])

    def test_enable_account_by_only_channel(self):
        """Test initializing account with single saved account."""
        subtests = ["ibm_cloud", "ibm_quantum"]
        for channel in subtests:
            with self.subTest(channel=channel):
                token = uuid.uuid4().hex
                with temporary_account_config_file(
                    channel=channel, token=token
                ), no_envs(["QISKIT_IBM_TOKEN"]):
                    service = FakeRuntimeService()
                self.assertTrue(service._account)
                self.assertEqual(service._account.token, token)
                expected = (
                    IBM_CLOUD_API_URL if channel == "ibm_cloud" else IBM_QUANTUM_API_URL
                )
                self.assertEqual(service._account.url, expected)
                self.assertEqual(service._account.channel, channel)

    def test_enable_account_both_channel(self):
        """Test initializing account with both saved types."""
        token = uuid.uuid4().hex
        contents = get_account_config_contents(channel="ibm_cloud", token=token)
        contents.update(
            get_account_config_contents(channel="ibm_quantum", token=uuid.uuid4().hex)
        )
        with temporary_account_config_file(contents=contents), no_envs(
            ["QISKIT_IBM_TOKEN"]
        ):
            service = FakeRuntimeService()
        self.assertTrue(service._account)
        self.assertEqual(service._account.token, token)
        self.assertEqual(service._account.url, IBM_CLOUD_API_URL)
        self.assertEqual(service._account.channel, "ibm_cloud")

    def test_enable_account_by_env_channel(self):
        """Test initializing account by environment variable and channel."""
        subtests = ["ibm_quantum", "ibm_cloud", None]
        for channel in subtests:
            with self.subTest(channel=channel):
                token = uuid.uuid4().hex
                url = uuid.uuid4().hex
                envs = {
                    "QISKIT_IBM_TOKEN": token,
                    "QISKIT_IBM_URL": url,
                    "QISKIT_IBM_INSTANCE": "h/g/p"
                    if channel == "ibm_quantum"
                    else "crn:12",
                }
                with custom_envs(envs):
                    service = FakeRuntimeService(channel=channel)

                self.assertTrue(service._account)
                self.assertEqual(service._account.token, token)
                self.assertEqual(service._account.url, url)
                channel = channel or "ibm_cloud"
                self.assertEqual(service._account.channel, channel)

    def test_enable_account_only_env_variables(self):
        """Test initializing account with only environment variables."""
        subtests = ["ibm_quantum", "ibm_cloud"]
        token = uuid.uuid4().hex
        url = uuid.uuid4().hex
        for channel in subtests:
            envs = {
                "QISKIT_IBM_TOKEN": token,
                "QISKIT_IBM_URL": url,
                "QISKIT_IBM_CHANNEL": channel,
                "QISKIT_IBM_INSTANCE": "h/g/p"
                if channel == "ibm_quantum"
                else "crn:12",
            }
            with custom_envs(envs):
                service = FakeRuntimeService()
            self.assertEqual(service._account.channel, channel)
            self.assertEqual(service._account.url, url)

    def test_enable_account_by_env_token_url(self):
        """Test initializing account by environment variable and extra."""
        token = uuid.uuid4().hex
        url = uuid.uuid4().hex
        envs = {
            "QISKIT_IBM_TOKEN": token,
            "QISKIT_IBM_URL": url,
            "QISKIT_IBM_INSTANCE": "my_crn",
        }
        subtests = [{"token": token}, {"url": url}, {"token": token, "url": url}]
        for extra in subtests:
            with self.subTest(extra=extra):
                with custom_envs(envs) as _, self.assertRaises(ValueError) as err:
                    _ = FakeRuntimeService(**extra)
                self.assertIn("token", str(err.exception))

    def test_enable_account_bad_name(self):
        """Test initializing account by bad name."""
        name = "phantom"
        with temporary_account_config_file() as _, self.assertRaises(
            AccountNotFoundError
        ) as err:
            _ = FakeRuntimeService(name=name)
        self.assertIn(name, str(err.exception))

    def test_enable_account_bad_channel(self):
        """Test initializing account by bad name."""
        channel = "phantom"
        with temporary_account_config_file() as _, self.assertRaises(ValueError) as err:
            _ = FakeRuntimeService(channel=channel)
        self.assertIn("channel", str(err.exception))

    def test_enable_account_by_name_pref(self):
        """Test initializing account by name and preferences."""
        name = "foo"
        subtests = [
            {"proxies": MOCK_PROXY_CONFIG_DICT},
            {"verify": False},
            {"instance": "bar"},
            {"proxies": MOCK_PROXY_CONFIG_DICT, "verify": False, "instance": "bar"},
        ]
        for extra in subtests:
            with self.subTest(extra=extra):
                with temporary_account_config_file(name=name, verify=True, proxies={}):
                    service = FakeRuntimeService(name=name, **extra)
                self.assertTrue(service._account)
                self._verify_prefs(extra, service._account)

    def test_enable_account_by_channel_pref(self):
        """Test initializing account by channel and preferences."""
        subtests = [
            {"proxies": MOCK_PROXY_CONFIG_DICT},
            {"verify": False},
            {"instance": "h/g/p"},
            {"proxies": MOCK_PROXY_CONFIG_DICT, "verify": False, "instance": "h/g/p"},
        ]
        for channel in ["ibm_cloud", "ibm_quantum"]:
            for extra in subtests:
                with self.subTest(
                    channel=channel, extra=extra
                ), temporary_account_config_file(
                    channel=channel, verify=True, proxies={}
                ), no_envs(
                    ["QISKIT_IBM_TOKEN"]
                ):
                    service = FakeRuntimeService(channel=channel, **extra)
                    self.assertTrue(service._account)
                    self._verify_prefs(extra, service._account)

    def test_enable_account_by_env_pref(self):
        """Test initializing account by environment variable and preferences."""
        subtests = [
            {"proxies": MOCK_PROXY_CONFIG_DICT},
            {"verify": False},
            {"instance": "bar"},
            {"proxies": MOCK_PROXY_CONFIG_DICT, "verify": False, "instance": "bar"},
        ]
        for extra in subtests:
            with self.subTest(extra=extra):
                token = uuid.uuid4().hex
                url = uuid.uuid4().hex
                envs = {
                    "QISKIT_IBM_TOKEN": token,
                    "QISKIT_IBM_URL": url,
                    "QISKIT_IBM_INSTANCE": "my_crn",
                }
                with custom_envs(envs):
                    service = FakeRuntimeService(**extra)

                self.assertTrue(service._account)
                self._verify_prefs(extra, service._account)

    def test_enable_account_by_name_input_instance(self):
        """Test initializing account by name and input instance."""
        name = "foo"
        instance = uuid.uuid4().hex
        with temporary_account_config_file(name=name, instance="stored-instance"):
            service = FakeRuntimeService(name=name, instance=instance)
        self.assertTrue(service._account)
        self.assertEqual(service._account.instance, instance)

    def test_enable_account_by_qiskitrc(self):
        """Test initializing account by a qiskitrc file."""
        token = "token-x"
        proxies = {"urls": {"https": "localhost:8080"}}
        str_contents = f"""
        [ibmq]
        token = {token}
        url = https://auth.quantum-computing.ibm.com/api
        verify = True
        default_provider = ibm-q/open/main
        proxies = {proxies}
        """
        with custom_qiskitrc(contents=str.encode(str_contents)):
            with temporary_account_config_file(contents={}):
                service = FakeRuntimeService()
        self.assertTrue(service._account)
        self.assertEqual(service._account.token, token)

    def test_enable_account_by_channel_input_instance(self):
        """Test initializing account by channel and input instance."""
        instance = uuid.uuid4().hex
        with temporary_account_config_file(channel="ibm_cloud", instance="bla"):
            service = FakeRuntimeService(channel="ibm_cloud", instance=instance)
        self.assertTrue(service._account)
        self.assertEqual(service._account.instance, instance)

    def test_enable_account_by_env_input_instance(self):
        """Test initializing account by env and input instance."""
        instance = uuid.uuid4().hex
        envs = {
            "QISKIT_IBM_TOKEN": "some_token",
            "QISKIT_IBM_URL": "some_url",
            "QISKIT_IBM_INSTANCE": "some_instance",
        }
        with custom_envs(envs):
            service = FakeRuntimeService(channel="ibm_cloud", instance=instance)
        self.assertTrue(service._account)
        self.assertEqual(service._account.instance, instance)

    def _verify_prefs(self, prefs, account):
        if "proxies" in prefs:
            self.assertEqual(account.proxies, ProxyConfiguration(**prefs["proxies"]))
        if "verify" in prefs:
            self.assertEqual(account.verify, prefs["verify"])
        if "instance" in prefs:
            self.assertEqual(account.instance, prefs["instance"])
