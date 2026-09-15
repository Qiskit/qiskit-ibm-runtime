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
import json
import logging
import os
import uuid
from typing import Any
from unittest import skipIf

from ddt import data, ddt

from qiskit_ibm_runtime import IBMInputValueError
from qiskit_ibm_runtime.accounts import (
    Account,
    AccountAlreadyExistsError,
    AccountManager,
    AccountNotFoundError,
    InvalidAccountError,
)
from qiskit_ibm_runtime.accounts.account import IBM_QUANTUM_PLATFORM_API_URL
from qiskit_ibm_runtime.accounts.management import (
    _DEFAULT_ACCOUNT_NAME_IBM_CLOUD,
    _DEFAULT_ACCOUNT_NAME_IBM_QUANTUM_PLATFORM,
)
from qiskit_ibm_runtime.proxies import ProxyConfiguration
from qiskit_ibm_runtime.qiskit_runtime_service import QiskitRuntimeService

from ..account import (
    custom_envs,
    get_account_config_contents,
    no_envs,
    temporary_account_config_file,
)
from ..decorators import mock_responses
from ..ibm_test_case import IBMTestCase
from ..utils import combine

_TEST_IBM_CLOUD_ACCOUNT = Account.create_account(
    channel="ibm_cloud",
    token="token-y",
    url="https://cloud.ibm.com",
    instance="crn:v1:bluemix:public:quantum-computing:us-east:a/...::",
    proxies=ProxyConfiguration(
        username_ntlm="bla", password_ntlm="blub", urls={"https": "127.0.0.1"}
    ),
)
_TEST_IBM_CLOUD_ACCOUNT_DICT = _TEST_IBM_CLOUD_ACCOUNT.to_saved_format()

_TEST_IBM_QUANTUM_PLATFORM_ACCOUNT = Account.create_account(
    channel="ibm_quantum_platform",
    token="token-y",
    url="https://quantum.cloud.ibm.com/api/v1",
    instance="crn:v1:bluemix:public:quantum-computing:us-east:a/...::",
    proxies=ProxyConfiguration(
        username_ntlm="bla", password_ntlm="blub", urls={"https": "127.0.0.1"}
    ),
)
_TEST_IBM_QUANTUM_PLATFORM_ACCOUNT_DICT = _TEST_IBM_QUANTUM_PLATFORM_ACCOUNT.to_saved_format()

_TEST_FILENAME = "/tmp/temp_qiskit_account.json"

_DEFAULT_CRN = "crn:v1:bluemix:public:quantum-computing:my-region:a/...:...::"


@ddt
class TestAccount(IBMTestCase):
    """Tests for Account class."""

    dummy_token = "123"
    dummy_ibm_cloud_url = "https://quantum.cloud.ibm.com"

    @data(_TEST_IBM_CLOUD_ACCOUNT, _TEST_IBM_QUANTUM_PLATFORM_ACCOUNT)
    def test_skip_crn_resolution_for_crn(self, test_account):
        """Test that CRN resolution is skipped if the instance value is already a CRN."""
        account = copy.deepcopy(test_account)
        account.resolve_crn()
        self.assertEqual(account.instance, test_account.instance)

    def test_invalid_channel(self):
        """Test invalid values for channel parameter."""
        with self.assertRaises(InvalidAccountError) as err:
            invalid_channel: Any = "phantom"
            Account.create_account(
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
                    Account.create_account(
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
                    Account.create_account(**params, token=self.dummy_token).validate()
                self.assertIn("Invalid `url` value.", str(err.exception))

    def test_invalid_account_prefs(self):
        """Test invalid values for account preferences."""
        with self.assertRaises(InvalidAccountError) as err:
            Account.create_account(
                channel="ibm_quantum_platform",
                token=self.dummy_token,
                url=self.dummy_ibm_cloud_url,
                region="invalid-region",
            ).validate()
        self.assertIn("Invalid `region` value.", str(err.exception))

        with self.assertRaises(InvalidAccountError) as err:
            Account.create_account(
                channel="ibm_quantum_platform",
                token=self.dummy_token,
                url=self.dummy_ibm_cloud_url,
                plans_preference="invalid-plans",
            ).validate()
        self.assertIn("Invalid `plans_preference` value.", str(err.exception))

        with self.assertRaises(InvalidAccountError) as err:
            Account.create_account(
                channel="ibm_quantum_platform",
                token=self.dummy_token,
                url=self.dummy_ibm_cloud_url,
                tags="invalid-tags",
            ).validate()
        self.assertIn("Invalid `tags` value.", str(err.exception))


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
        user_filename = _TEST_FILENAME
        sub_tests = [
            # verify accounts can be saved and retrieved via custom names
            (_TEST_IBM_CLOUD_ACCOUNT, None, "acct-2", "acct-2"),
            (_TEST_IBM_QUANTUM_PLATFORM_ACCOUNT, None, "acct-3", "acct-3"),
            # verify default account name handling for ibm_cloud accounts
            (
                _TEST_IBM_QUANTUM_PLATFORM_ACCOUNT,
                None,
                None,
                _DEFAULT_ACCOUNT_NAME_IBM_QUANTUM_PLATFORM,
            ),
            (_TEST_IBM_QUANTUM_PLATFORM_ACCOUNT, None, None, None),
            # verify account override
            (_TEST_IBM_CLOUD_ACCOUNT, None, "acct", "acct"),
            (_TEST_IBM_QUANTUM_PLATFORM_ACCOUNT, None, "acct", "acct"),
            # same as above with filename
            (_TEST_IBM_CLOUD_ACCOUNT, user_filename, "acct-2", "acct-2"),
            (_TEST_IBM_QUANTUM_PLATFORM_ACCOUNT, user_filename, "acct-3", "acct-3"),
            # verify default account name handling for ibm_cloud accounts
            (
                _TEST_IBM_QUANTUM_PLATFORM_ACCOUNT,
                user_filename,
                None,
                _DEFAULT_ACCOUNT_NAME_IBM_QUANTUM_PLATFORM,
            ),
            (_TEST_IBM_QUANTUM_PLATFORM_ACCOUNT, user_filename, None, None),
            # verify account override
            (_TEST_IBM_CLOUD_ACCOUNT, user_filename, "acct", "acct"),
            (_TEST_IBM_QUANTUM_PLATFORM_ACCOUNT, user_filename, "acct", "acct"),
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
                self.assertEqual(account, AccountManager.get(filename=file_name, name=name_get))

    @temporary_account_config_file(
        contents=json.dumps(
            {
                "ibm_cloud": _TEST_IBM_CLOUD_ACCOUNT_DICT,
                "ibm_quantum_platform": _TEST_IBM_QUANTUM_PLATFORM_ACCOUNT_DICT,
            }
        )
    )
    def test_list(self):
        """Test list."""
        test_ibm_quantum_classic_account = {
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

        with (
            temporary_account_config_file(
                contents={
                    "key1": _TEST_IBM_CLOUD_ACCOUNT_DICT,
                    "key2": _TEST_IBM_QUANTUM_PLATFORM_ACCOUNT_DICT,
                    "key3": test_ibm_quantum_classic_account,
                }
            ),
            self.subTest("non-empty list of accounts"),
        ):
            accounts = AccountManager.list()
            self.assertEqual(len(accounts), 2)
            self.assertEqual(accounts["key1"], _TEST_IBM_CLOUD_ACCOUNT)
            self.assertTrue(accounts["key2"], _TEST_IBM_QUANTUM_PLATFORM_ACCOUNT)

        with (
            temporary_account_config_file(
                contents={
                    "key1": _TEST_IBM_CLOUD_ACCOUNT_DICT,
                    "key2": _TEST_IBM_QUANTUM_PLATFORM_ACCOUNT_DICT,
                    _DEFAULT_ACCOUNT_NAME_IBM_CLOUD: Account.create_account(
                        channel="ibm_cloud", token="token-ibm-cloud", instance="crn:123"
                    ).to_saved_format(),
                    _DEFAULT_ACCOUNT_NAME_IBM_QUANTUM_PLATFORM: Account.create_account(
                        channel="ibm_quantum_platform", token="token-ibm-cloud", instance="crn:123"
                    ).to_saved_format(),
                }
            ),
            self.subTest("filtered list of accounts"),
        ):
            accounts = list(AccountManager.list(channel="ibm_quantum_platform").keys())
            self.assertEqual(len(accounts), 2)
            self.assertListEqual(accounts, ["key2", _DEFAULT_ACCOUNT_NAME_IBM_QUANTUM_PLATFORM])

            accounts = list(
                AccountManager.list(channel="ibm_quantum_platform", default=False).keys()
            )
            self.assertEqual(len(accounts), 1)
            self.assertListEqual(accounts, ["key2"])

            accounts = list(AccountManager.list(name="key1").keys())
            self.assertEqual(len(accounts), 1)
            self.assertListEqual(accounts, ["key1"])

    @temporary_account_config_file(
        contents={
            "key1": _TEST_IBM_CLOUD_ACCOUNT_DICT,
            _DEFAULT_ACCOUNT_NAME_IBM_CLOUD: _TEST_IBM_CLOUD_ACCOUNT_DICT,
            _DEFAULT_ACCOUNT_NAME_IBM_QUANTUM_PLATFORM: _TEST_IBM_QUANTUM_PLATFORM_ACCOUNT_DICT,
        }
    )
    def test_delete(self):
        """Test delete."""
        with self.subTest("delete named account"):
            self.assertTrue(AccountManager.delete(name="key1"))
            self.assertFalse(AccountManager.delete(name="key1"))

        with self.subTest("delete default ibm_cloud account"):
            self.assertTrue(AccountManager.delete(channel="ibm_cloud"))
            self.assertTrue(len(AccountManager.list()) == 1)
        with self.subTest("delete default ibm_quantum_platform account"):
            self.assertTrue(AccountManager.delete())
            self.assertTrue(len(AccountManager.list()) == 0)

    def test_delete_filename(self):
        """Test delete accounts with filename parameter."""
        filename = _TEST_FILENAME
        name = "key1"
        channel = "ibm_quantum_platform"
        AccountManager.save(channel=channel, filename=filename, name=name, token="temp_token")
        self.assertTrue(
            AccountManager.delete(channel="ibm_quantum_platform", filename=filename, name=name)
        )
        self.assertFalse(
            AccountManager.delete(channel="ibm_quantum_platform", filename=filename, name=name)
        )

        self.assertTrue(
            len(AccountManager.list(channel="ibm_quantum_platform", filename=filename)) == 0
        )

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
        self.assertEqual(account.token, dummy_token)

    @mock_responses
    @temporary_account_config_file()
    def test_default_env_channel(self, registry):
        """Test that if QISKIT_IBM_CHANNEL is set in the environment, this channel will be used."""
        token = uuid.uuid4().hex
        # unset default_channel in the environment
        with temporary_account_config_file(token=token), no_envs("QISKIT_IBM_CHANNEL"):
            service = QiskitRuntimeService()
            self.assertEqual(service.channel, "ibm_quantum_platform")

        # set channel to default channel in the environment
        subtests = ["ibm_quantum_platform"]
        for channel in subtests:
            channel_env = {"QISKIT_IBM_CHANNEL": channel}
            with (
                temporary_account_config_file(channel=channel, token=token),
                custom_envs(channel_env),
            ):
                service = QiskitRuntimeService()
                self.assertEqual(service.channel, channel)

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
        self.assertTrue(account.private_endpoint)

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
        self.assertEqual(account.channel, "ibm_quantum_platform")
        self.assertEqual(account.token, _TEST_IBM_CLOUD_ACCOUNT.token)

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
            self.assertEqual(service.channel, "ibm_quantum_platform")
            self.assertEqual(service._account.token, any_token)

        # No name or channel params, no env vars, get the account specified as "is_default_account"
        with (
            temporary_account_config_file(contents=contents),
            no_envs("QISKIT_IBM_CHANNEL"),
            no_envs("QISKIT_IBM_TOKEN"),
        ):
            service = QiskitRuntimeService()
            self.assertEqual(service.channel, "ibm_quantum_platform")
            self.assertEqual(service._account.token, preferred_token)

        # parameter 'channel' is specified, it overrides channel in env
        # account specified as "is_default_account"
        with (
            temporary_account_config_file(contents=contents),
            custom_envs(channel_env),
            no_envs("QISKIT_IBM_TOKEN"),
        ):
            service = QiskitRuntimeService(channel="ibm_quantum_platform")
            self.assertEqual(service.channel, "ibm_quantum_platform")
            self.assertEqual(service._account.token, preferred_token)

        # account with default name for the channel
        contents["preferred-ibm-quantum"]["is_default_account"] = False
        with (
            temporary_account_config_file(contents=contents),
            custom_envs(channel_env),
            no_envs("QISKIT_IBM_TOKEN"),
        ):
            service = QiskitRuntimeService(channel="ibm_quantum_platform")
            self.assertEqual(service.channel, "ibm_quantum_platform")
            self.assertEqual(service._account.token, cloud_token)

        # any account for this channel
        with (
            temporary_account_config_file(contents=contents),
            custom_envs(channel_env),
            no_envs("QISKIT_IBM_TOKEN"),
        ):
            service = QiskitRuntimeService(channel="ibm_quantum_platform")
            self.assertEqual(service.channel, "ibm_quantum_platform")
            self.assertEqual(service._account.token, cloud_token)

        # no channel param, get account that is specified as "is_default_account"
        # for channel from env
        contents["preferred-ibm-quantum"]["is_default_account"] = True
        with (
            temporary_account_config_file(contents=contents),
            custom_envs(channel_env),
            no_envs("QISKIT_IBM_TOKEN"),
        ):
            service = QiskitRuntimeService()
            self.assertEqual(service.channel, "ibm_quantum_platform")
            self.assertEqual(service._account.token, preferred_token)

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
            self.assertEqual(service.channel, "ibm_quantum_platform")
            self.assertEqual(service._account.token, cloud_token)

        # no channel param, any account for the channel from env
        del contents["default-ibm-quantum"]
        with (
            temporary_account_config_file(contents=contents),
            custom_envs(channel_env),
            no_envs("QISKIT_IBM_TOKEN"),
        ):
            service = QiskitRuntimeService()
            self.assertEqual(service.channel, "ibm_quantum_platform")
            self.assertEqual(service._account.token, cloud_token)
        # default channel
        with temporary_account_config_file(contents=contents), no_envs("QISKIT_IBM_CHANNEL"):
            service = QiskitRuntimeService()
            self.assertEqual(service.channel, "ibm_quantum_platform")

    def tearDown(self) -> None:
        """Test level tear down."""
        super().tearDown()
        if os.path.exists(_TEST_FILENAME):
            os.remove(_TEST_FILENAME)


MOCK_PROXY_CONFIG_DICT = {"urls": {"https": "127.0.0.1", "username_ntlm": "", "password_ntlm": ""}}


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

        self.assertTrue(service._account)
        self.assertEqual(service._account.token, token)

    @mock_responses
    @data("ibm_quantum_platform", "ibm_cloud")
    def test_enable_account_by_channel(self, channel, registry):
        """Test initializing account by channel."""
        with no_envs(["QISKIT_IBM_TOKEN"]):
            token = uuid.uuid4().hex
            with temporary_account_config_file(channel=channel, token=token):
                service = QiskitRuntimeService(channel=channel)
            self.assertTrue(service._account)
            self.assertEqual(service._account.token, token)

    @mock_responses
    @data(
        {"token": uuid.uuid4().hex}, {"token": uuid.uuid4().hex, "url": "https://foo.cloud.ibm.com"}
    )
    def test_enable_account_by_token_url(self, params, registry):
        """Test initializing account by token."""
        with temporary_account_config_file(channel="ibm_quantum_platform", token=params["token"]):
            service = QiskitRuntimeService(**params)
            self.assertTrue(service._account)

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

            self.assertTrue(service._account)
            self.assertEqual(service._account.token, token)
            self.assertIn("are ignored", logged.output[0])

    @mock_responses
    @data(None, "https://foo.cloud.ibm.com")
    def test_enable_cloud_account_by_channel_token_url(self, url, registry):
        """Test initializing cloud account by channel, token, url."""
        with no_envs(["QISKIT_IBM_TOKEN"]):
            token = uuid.uuid4().hex
            service = QiskitRuntimeService(channel="ibm_quantum_platform", token=token, url=url)
            self.assertTrue(service)

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

        self.assertTrue(service._account)
        self.assertEqual(service._account.token, token)
        expected = IBM_QUANTUM_PLATFORM_API_URL
        self.assertEqual(service._account.url, expected)
        self.assertIn("url", logged.output[0])

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
        self.assertTrue(service._account)
        self.assertEqual(service._account.token, token)
        expected = IBM_QUANTUM_PLATFORM_API_URL
        self.assertEqual(service._account.url, expected)
        self.assertEqual(service._account.channel, channel)

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
        self.assertTrue(service._account)
        self.assertEqual(service._account.token, token)
        self.assertEqual(service._account.url, IBM_QUANTUM_PLATFORM_API_URL)
        self.assertEqual(service._account.channel, "ibm_quantum_platform")

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

        self.assertTrue(service._account)
        self.assertEqual(service._account.token, token)
        self.assertEqual(service._account.url, url)
        channel = channel or "ibm_quantum_platform"
        self.assertEqual(service._account.channel, channel)

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
        self.assertEqual(service._account.channel, channel or "ibm_quantum_platform")
        self.assertEqual(service._account.url, url)

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
            self.assertTrue(service._account)

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
        self.assertTrue(service._account)
        self._verify_prefs(params, service._account)

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
            self.assertTrue(service._account)
            self._verify_prefs(params, service._account)

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

        self.assertTrue(service._account)
        self._verify_prefs(params, service._account)

    @mock_responses
    def test_enable_account_by_name_input_instance(self, registry):
        """Test initializing account by name and input instance."""
        name = "foo"
        instance = _DEFAULT_CRN
        with temporary_account_config_file(name=name, instance="stored-instance"):
            service = QiskitRuntimeService(name=name, instance=instance)
        self.assertTrue(service._account)
        self.assertEqual(service._account.instance, instance)

    @mock_responses
    def test_enable_account_by_channel_input_instance(self, registry):
        """Test initializing account by channel and input instance."""
        instance = _DEFAULT_CRN
        with temporary_account_config_file(channel="ibm_quantum_platform", instance="bla"):
            service = QiskitRuntimeService(channel="ibm_quantum_platform", instance=instance)
        self.assertTrue(service._account)
        self.assertEqual(service._account.instance, instance)

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
        self.assertTrue(service._account)
        self.assertEqual(service._account.instance, instance)

    @mock_responses
    def test_instance_filter_tags(self, registry):
        """Test initializing account by channel and input instance."""
        registry.instances["a"].tags = ["services"]

        tags = ["services"]
        with temporary_account_config_file(channel="ibm_quantum_platform"):
            service = QiskitRuntimeService(channel="ibm_quantum_platform", tags=tags)
            self.assertTrue(service._account)
            for inst in service._backend_instance_groups:
                self.assertEqual(inst["tags"], tags)

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
        self.assertTrue(service._instance_auto)
        self.assertIsNone(service._account.instance)

    @mock_responses
    def test_instance_auto_suppresses_init_warning(self, registry):
        """instance='auto' must not trigger the 'instance was not set' warning during init."""
        # "Loading account with the given token" warning fires regardless; check only for
        # the absence of the specific instance warning. Contrast with no-instance service.
        with self.assertLogs("qiskit_ibm_runtime", level="WARNING") as logs:
            QiskitRuntimeService(channel="ibm_quantum_platform", token="my_token")
        self.assertTrue(any("Instance was not set" in msg for msg in logs.output))

        with self.assertLogs("qiskit_ibm_runtime", level="WARNING") as logs:
            QiskitRuntimeService(channel="ibm_quantum_platform", token="my_token", instance="auto")
        self.assertFalse(any("Instance was not set" in msg for msg in logs.output))

    @mock_responses
    def test_saved_account_instance_auto_sets_flag(self, registry):
        """A saved account with instance='auto' sets _instance_auto and clears the instance."""
        with temporary_account_config_file(
            channel="ibm_quantum_platform", token="my_token", instance="auto"
        ):
            service = QiskitRuntimeService()
        self.assertTrue(service._instance_auto)
        self.assertIsNone(service._account.instance)

    def _verify_prefs(self, prefs, account):
        if "proxies" in prefs:
            self.assertEqual(account.proxies, ProxyConfiguration(**prefs["proxies"]))
        if "verify" in prefs:
            self.assertEqual(account.verify, prefs["verify"])
        if "instance" in prefs:
            self.assertEqual(account.instance, prefs["instance"])
