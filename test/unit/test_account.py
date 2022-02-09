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
    management,
    AccountAlreadyExistsError,
    AccountNotFoundError,
    InvalidAccountError,
)
from qiskit_ibm_runtime.accounts.account import CLOUD_API_URL, LEGACY_API_URL
from qiskit_ibm_runtime.proxies import ProxyConfiguration
from .mock.fake_runtime_service import FakeRuntimeService
from ..ibm_test_case import IBMTestCase
from ..account import (
    get_account_config_contents,
    temporary_account_config_file,
    no_envs,
    custom_envs,
)

_TEST_LEGACY_ACCOUNT = Account(
    auth="legacy",
    token="token-x",
    url="https://auth.quantum-computing.ibm.com/api",
    instance="ibm-q/open/main",
)

_TEST_CLOUD_ACCOUNT = Account(
    auth="cloud",
    token="token-y",
    url="https://cloud.ibm.com",
    instance="crn:v1:bluemix:public:quantum-computing:us-east:a/...::",
    proxies=ProxyConfiguration(
        username_ntlm="bla", password_ntlm="blub", urls={"https": "127.0.0.1"}
    ),
)


class TestAccount(IBMTestCase):
    """Tests for Account class."""

    dummy_token = "123"
    dummy_cloud_url = "https://us-east.quantum-computing.cloud.ibm.com"
    dummy_legacy_url = "https://auth.quantum-computing.ibm.com/api"

    def test_skip_crn_resolution_for_crn(self):
        """Test that CRN resolution is skipped if the instance value is already a CRN."""
        account = copy.deepcopy(_TEST_CLOUD_ACCOUNT)
        account.resolve_crn()
        self.assertEqual(account.instance, _TEST_CLOUD_ACCOUNT.instance)

    def test_invalid_auth(self):
        """Test invalid values for auth parameter."""

        with self.assertRaises(InvalidAccountError) as err:
            invalid_auth: Any = "phantom"
            Account(
                auth=invalid_auth, token=self.dummy_token, url=self.dummy_cloud_url
            ).validate()
        self.assertIn("Invalid `auth` value.", str(err.exception))

    def test_invalid_token(self):
        """Test invalid values for token parameter."""

        invalid_tokens = [1, None, ""]
        for token in invalid_tokens:
            with self.subTest(token=token):
                with self.assertRaises(InvalidAccountError) as err:
                    Account(
                        auth="cloud", token=token, url=self.dummy_cloud_url
                    ).validate()
                self.assertIn("Invalid `token` value.", str(err.exception))

    def test_invalid_url(self):
        """Test invalid values for url parameter."""

        subtests = [
            {"auth": "cloud", "url": 123},
        ]
        for params in subtests:
            with self.subTest(params=params):
                with self.assertRaises(InvalidAccountError) as err:
                    Account(**params, token=self.dummy_token).validate()
                self.assertIn("Invalid `url` value.", str(err.exception))

    def test_invalid_instance(self):
        """Test invalid values for instance parameter."""

        subtests = [
            {"auth": "cloud", "instance": ""},
            {"auth": "cloud"},
            {"auth": "legacy", "instance": "no-hgp-format"},
        ]
        for params in subtests:
            with self.subTest(params=params):
                with self.assertRaises(InvalidAccountError) as err:
                    Account(
                        **params, token=self.dummy_token, url=self.dummy_cloud_url
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
                        auth="legacy",
                        token=self.dummy_token,
                        url=self.dummy_cloud_url,
                    ).validate()
                self.assertIn("Invalid proxy configuration", str(err.exception))


# NamedTemporaryFiles not supported in Windows
@skipIf(os.name == "nt", "Test not supported in Windows")
class TestAccountManager(IBMTestCase):
    """Tests for AccountManager class."""

    @temporary_account_config_file(
        contents={"conflict": _TEST_CLOUD_ACCOUNT.to_saved_format()}
    )
    def test_save_without_override(self):
        """Test to override an existing account without setting overwrite=True."""
        with self.assertRaises(AccountAlreadyExistsError):
            AccountManager.save(
                name="conflict",
                token=_TEST_CLOUD_ACCOUNT.token,
                url=_TEST_CLOUD_ACCOUNT.url,
                instance=_TEST_CLOUD_ACCOUNT.instance,
                auth="cloud",
                overwrite=False,
            )

    @temporary_account_config_file(
        contents={"conflict": _TEST_CLOUD_ACCOUNT.to_saved_format()}
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
        sub_tests = [
            # verify accounts can be saved and retrieved via custom names
            (_TEST_LEGACY_ACCOUNT, "acct-1", "acct-1"),
            (_TEST_CLOUD_ACCOUNT, "acct-2", "acct-2"),
            # verify default account name handling for cloud accounts
            (_TEST_CLOUD_ACCOUNT, None, management._DEFAULT_ACCOUNT_NAME_CLOUD),
            (_TEST_CLOUD_ACCOUNT, None, None),
            # verify default account name handling for legacy accounts
            (_TEST_LEGACY_ACCOUNT, None, management._DEFAULT_ACCOUNT_NAME_LEGACY),
            # verify account override
            (_TEST_LEGACY_ACCOUNT, "acct", "acct"),
            (_TEST_CLOUD_ACCOUNT, "acct", "acct"),
        ]
        for account, name_save, name_get in sub_tests:
            with self.subTest(
                f"for account type '{account.auth}' "
                f"using `save(name={name_save})` and `get(name={name_get})`"
            ):
                AccountManager.save(
                    token=account.token,
                    url=account.url,
                    instance=account.instance,
                    auth=account.auth,
                    proxies=account.proxies,
                    verify=account.verify,
                    name=name_save,
                    overwrite=True,
                )
                self.assertEqual(account, AccountManager.get(name=name_get))

    @temporary_account_config_file(
        contents=json.dumps(
            {
                "cloud": _TEST_CLOUD_ACCOUNT.to_saved_format(),
                "legacy": _TEST_LEGACY_ACCOUNT.to_saved_format(),
            }
        )
    )
    def test_list(self):
        """Test list."""

        with temporary_account_config_file(
            contents={
                "key1": _TEST_CLOUD_ACCOUNT.to_saved_format(),
                "key2": _TEST_LEGACY_ACCOUNT.to_saved_format(),
            }
        ), self.subTest("non-empty list of accounts"):
            accounts = AccountManager.list()

            self.assertEqual(len(accounts), 2)
            self.assertEqual(accounts["key1"], _TEST_CLOUD_ACCOUNT)
            self.assertTrue(accounts["key2"], _TEST_LEGACY_ACCOUNT)

        with temporary_account_config_file(contents={}), self.subTest(
            "empty list of accounts"
        ):
            self.assertEqual(len(AccountManager.list()), 0)

        with temporary_account_config_file(
            contents={
                "key1": _TEST_CLOUD_ACCOUNT.to_saved_format(),
                "key2": _TEST_LEGACY_ACCOUNT.to_saved_format(),
                management._DEFAULT_ACCOUNT_NAME_CLOUD: Account(
                    "cloud", "token-cloud", instance="crn:123"
                ).to_saved_format(),
                management._DEFAULT_ACCOUNT_NAME_LEGACY: Account(
                    "legacy", "token-legacy"
                ).to_saved_format(),
            }
        ), self.subTest("filtered list of accounts"):
            accounts = list(AccountManager.list(auth="cloud").keys())
            self.assertEqual(len(accounts), 2)
            self.assertListEqual(
                accounts, ["key1", management._DEFAULT_ACCOUNT_NAME_CLOUD]
            )

            accounts = list(AccountManager.list(auth="legacy").keys())
            self.assertEqual(len(accounts), 2)
            self.assertListEqual(
                accounts, ["key2", management._DEFAULT_ACCOUNT_NAME_LEGACY]
            )

            accounts = list(AccountManager.list(auth="cloud", default=True).keys())
            self.assertEqual(len(accounts), 1)
            self.assertListEqual(accounts, [management._DEFAULT_ACCOUNT_NAME_CLOUD])

            accounts = list(AccountManager.list(auth="cloud", default=False).keys())
            self.assertEqual(len(accounts), 1)
            self.assertListEqual(accounts, ["key1"])

            accounts = list(AccountManager.list(name="key1").keys())
            self.assertEqual(len(accounts), 1)
            self.assertListEqual(accounts, ["key1"])

    @temporary_account_config_file(
        contents={
            "key1": _TEST_CLOUD_ACCOUNT.to_saved_format(),
            management._DEFAULT_ACCOUNT_NAME_LEGACY: _TEST_LEGACY_ACCOUNT.to_saved_format(),
            management._DEFAULT_ACCOUNT_NAME_CLOUD: _TEST_CLOUD_ACCOUNT.to_saved_format(),
        }
    )
    def test_delete(self):
        """Test delete."""

        with self.subTest("delete named account"):
            self.assertTrue(AccountManager.delete(name="key1"))
            self.assertFalse(AccountManager.delete(name="key1"))

        with self.subTest("delete default legacy account"):
            self.assertTrue(AccountManager.delete(auth="legacy"))

        with self.subTest("delete default cloud account"):
            self.assertTrue(AccountManager.delete())

        self.assertTrue(len(AccountManager.list()) == 0)


MOCK_PROXY_CONFIG_DICT = {
    "urls": {"https": "127.0.0.1", "username_ntlm": "", "password_ntlm": ""}
}
# NamedTemporaryFiles not supported in Windows
@skipIf(os.name == "nt", "Test not supported in Windows")
class TestEnableAccount(IBMTestCase):
    """Tests for IBMRuntimeService enable account."""

    def test_enable_account_by_name(self):
        """Test initializing account by name."""
        name = "foo"
        token = uuid.uuid4().hex
        with temporary_account_config_file(name=name, token=token):
            service = FakeRuntimeService(name=name)

        self.assertTrue(service._account)
        self.assertEqual(service._account.token, token)

    def test_enable_account_by_auth(self):
        """Test initializing account by auth."""
        for auth in ["cloud", "legacy"]:
            with self.subTest(auth=auth), no_envs(["QISKIT_IBM_TOKEN"]):
                token = uuid.uuid4().hex
                with temporary_account_config_file(auth=auth, token=token):
                    service = FakeRuntimeService(auth=auth)
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
            {"auth": "cloud"},
            {"token": "some_token"},
            {"url": "some_url"},
            {"auth": "cloud", "token": "some_token", "url": "some_url"},
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

    def test_enable_cloud_account_by_auth_token_url(self):
        """Test initializing cloud account by auth, token, url."""
        # Enable account will fail due to missing CRN.
        urls = [None, "some_url"]
        for url in urls:
            with self.subTest(url=url), no_envs(["QISKIT_IBM_TOKEN"]):
                token = uuid.uuid4().hex
                with self.assertRaises(InvalidAccountError) as err:
                    _ = FakeRuntimeService(auth="cloud", token=token, url=url)
                self.assertIn("instance", str(err.exception))

    def test_enable_legacy_account_by_auth_token_url(self):
        """Test initializing legacy account by auth, token, url."""
        urls = [(None, LEGACY_API_URL), ("some_url", "some_url")]
        for url, expected in urls:
            with self.subTest(url=url), no_envs(["QISKIT_IBM_TOKEN"]):
                token = uuid.uuid4().hex
                service = FakeRuntimeService(auth="legacy", token=token, url=url)
                self.assertTrue(service._account)
                self.assertEqual(service._account.token, token)
                self.assertEqual(service._account.url, expected)

    def test_enable_account_by_auth_url(self):
        """Test initializing legacy account by auth, token, url."""
        subtests = ["legacy", "cloud"]
        for auth in subtests:
            with self.subTest(auth=auth):
                token = uuid.uuid4().hex
                with temporary_account_config_file(auth=auth, token=token), no_envs(
                    ["QISKIT_IBM_TOKEN"]
                ):
                    with self.assertLogs(
                        "qiskit_ibm_runtime", logging.WARNING
                    ) as logged:
                        service = FakeRuntimeService(auth=auth, url="some_url")

                self.assertTrue(service._account)
                self.assertEqual(service._account.token, token)
                expected = CLOUD_API_URL if auth == "cloud" else LEGACY_API_URL
                self.assertEqual(service._account.url, expected)
                self.assertIn("url", logged.output[0])

    def test_enable_account_by_only_auth(self):
        """Test initializing account with single saved account."""
        subtests = ["legacy", "cloud"]
        for auth in subtests:
            with self.subTest(auth=auth):
                token = uuid.uuid4().hex
                with temporary_account_config_file(auth=auth, token=token), no_envs(
                    ["QISKIT_IBM_TOKEN"]
                ):
                    service = FakeRuntimeService()
                self.assertTrue(service._account)
                self.assertEqual(service._account.token, token)
                expected = CLOUD_API_URL if auth == "cloud" else LEGACY_API_URL
                self.assertEqual(service._account.url, expected)
                self.assertEqual(service._account.auth, auth)

    def test_enable_account_both_auth(self):
        """Test initializing account with both saved types."""
        token = uuid.uuid4().hex
        contents = get_account_config_contents(auth="cloud", token=token)
        contents.update(
            get_account_config_contents(auth="legacy", token=uuid.uuid4().hex)
        )
        with temporary_account_config_file(contents=contents), no_envs(
            ["QISKIT_IBM_TOKEN"]
        ):
            service = FakeRuntimeService()
        self.assertTrue(service._account)
        self.assertEqual(service._account.token, token)
        self.assertEqual(service._account.url, CLOUD_API_URL)
        self.assertEqual(service._account.auth, "cloud")

    def test_enable_account_by_env_auth(self):
        """Test initializing account by environment variable and auth."""
        subtests = ["legacy", "cloud", None]
        for auth in subtests:
            with self.subTest(auth=auth):
                token = uuid.uuid4().hex
                url = uuid.uuid4().hex
                envs = {
                    "QISKIT_IBM_TOKEN": token,
                    "QISKIT_IBM_URL": url,
                    "QISKIT_IBM_INSTANCE": "h/g/p" if auth == "legacy" else "crn:123",
                }
                with custom_envs(envs):
                    service = FakeRuntimeService(auth=auth)

                self.assertTrue(service._account)
                self.assertEqual(service._account.token, token)
                self.assertEqual(service._account.url, url)
                auth = auth or "cloud"
                self.assertEqual(service._account.auth, auth)

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

    def test_enable_account_bad_auth(self):
        """Test initializing account by bad name."""
        auth = "phantom"
        with temporary_account_config_file() as _, self.assertRaises(ValueError) as err:
            _ = FakeRuntimeService(auth=auth)
        self.assertIn("auth", str(err.exception))

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
                with temporary_account_config_file(
                    name=name, verify=True, proxies="some proxies"
                ):
                    service = FakeRuntimeService(name=name, **extra)
                self.assertTrue(service._account)
                self._verify_prefs(extra, service._account)

    def test_enable_account_by_auth_pref(self):
        """Test initializing account by auth and preferences."""
        subtests = [
            {"proxies": MOCK_PROXY_CONFIG_DICT},
            {"verify": False},
            {"instance": "h/g/p"},
            {"proxies": MOCK_PROXY_CONFIG_DICT, "verify": False, "instance": "h/g/p"},
        ]
        for auth in ["cloud", "legacy"]:
            for extra in subtests:
                with self.subTest(
                    auth=auth, extra=extra
                ), temporary_account_config_file(
                    auth=auth, verify=True, proxies="some proxies"
                ), no_envs(
                    ["QISKIT_IBM_TOKEN"]
                ):
                    service = FakeRuntimeService(auth=auth, **extra)
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

    def test_enable_account_by_auth_input_instance(self):
        """Test initializing account by auth and input instance."""
        instance = uuid.uuid4().hex
        with temporary_account_config_file(auth="cloud", instance="bla"):
            service = FakeRuntimeService(auth="cloud", instance=instance)
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
            service = FakeRuntimeService(auth="cloud", instance=instance)
        self.assertTrue(service._account)
        self.assertEqual(service._account.instance, instance)

    def _verify_prefs(self, prefs, account):
        if "proxies" in prefs:
            self.assertEqual(account.proxies, ProxyConfiguration(**prefs["proxies"]))
        if "verify" in prefs:
            self.assertEqual(account.verify, prefs["verify"])
        if "instance" in prefs:
            self.assertEqual(account.instance, prefs["instance"])
