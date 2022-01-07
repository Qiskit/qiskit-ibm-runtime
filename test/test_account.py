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

import json
import uuid
import logging
import os
from unittest import skipIf

from qiskit_ibm_runtime.accounts.account import CLOUD_API_URL, LEGACY_API_URL
from qiskit_ibm_runtime.accounts import AccountManager, Account, management
from qiskit_ibm_runtime.exceptions import IBMInputValueError

from .ibm_test_case import IBMTestCase
from .mock.fake_runtime_service import FakeRuntimeService
from .utils.account import (
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
)


# NamedTemporaryFiles not supported in Windows
@skipIf(os.name == "nt", "Test not supported in Windows")
class TestAccountManager(IBMTestCase):
    """Tests for AccountManager class."""

    @temporary_account_config_file(contents={})
    @no_envs(["QISKIT_IBM_API_TOKEN"])
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
                    "cloud", "token-legacy"
                ).to_saved_format(),
                management._DEFAULT_ACCOUNT_NAME_LEGACY: Account(
                    "legacy", "token-cloud"
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
            with self.subTest(auth=auth), no_envs(["QISKIT_IBM_API_TOKEN"]):
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
            with self.subTest(url=url), no_envs(["QISKIT_IBM_API_TOKEN"]):
                token = uuid.uuid4().hex
                with self.assertRaises(IBMInputValueError) as err:
                    _ = FakeRuntimeService(auth="cloud", token=token, url=url)
                self.assertIn("instance", str(err.exception))

    def test_enable_legacy_account_by_auth_token_url(self):
        """Test initializing legacy account by auth, token, url."""
        urls = [(None, LEGACY_API_URL), ("some_url", "some_url")]
        for url, expected in urls:
            with self.subTest(url=url), no_envs(["QISKIT_IBM_API_TOKEN"]):
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
                    ["QISKIT_IBM_API_TOKEN"]
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
                    ["QISKIT_IBM_API_TOKEN"]
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
            ["QISKIT_IBM_API_TOKEN"]
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
                    "QISKIT_IBM_API_TOKEN": token,
                    "QISKIT_IBM_API_URL": url,
                    "QISKIT_IBM_INSTANCE": "my_crn",
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
            "QISKIT_IBM_API_TOKEN": token,
            "QISKIT_IBM_API_URL": url,
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
        with temporary_account_config_file() as _, self.assertRaises(ValueError) as err:
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
            {"proxies": "foo"},
            {"verify": False},
            {"instance": "bar"},
            {"proxies": "foo", "verify": False, "instance": "bar"},
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
            {"proxies": "foo"},
            {"verify": False},
            {"instance": "bar"},
            {"proxies": "foo", "verify": False, "instance": "bar"},
        ]
        for auth in ["cloud", "legacy"]:
            for extra in subtests:
                with self.subTest(
                    auth=auth, extra=extra
                ), temporary_account_config_file(
                    auth=auth, verify=True, proxies="some proxies"
                ), no_envs(
                    ["QISKIT_IBM_API_TOKEN"]
                ):
                    service = FakeRuntimeService(auth=auth, **extra)
                    self.assertTrue(service._account)
                    self._verify_prefs(extra, service._account)

    def test_enable_account_by_env_pref(self):
        """Test initializing account by environment variable and preferences."""
        subtests = [
            {"proxies": "foo"},
            {"verify": False},
            {"instance": "bar"},
            {"proxies": "foo", "verify": False, "instance": "bar"},
        ]
        for extra in subtests:
            with self.subTest(extra=extra):
                token = uuid.uuid4().hex
                url = uuid.uuid4().hex
                envs = {
                    "QISKIT_IBM_API_TOKEN": token,
                    "QISKIT_IBM_API_URL": url,
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
        with temporary_account_config_file(name=name, instance=""):
            service = FakeRuntimeService(name=name, instance=instance)
        self.assertTrue(service._account)
        self.assertEqual(service._account.instance, instance)

    def test_enable_account_by_auth_input_instance(self):
        """Test initializing account by auth and input instance."""
        instance = uuid.uuid4().hex
        with temporary_account_config_file(auth="cloud", instance=""):
            service = FakeRuntimeService(auth="cloud", instance=instance)
        self.assertTrue(service._account)
        self.assertEqual(service._account.instance, instance)

    def test_enable_account_by_env_input_instance(self):
        """Test initializing account by env and input instance."""
        instance = uuid.uuid4().hex
        envs = {"QISKIT_IBM_API_TOKEN": "some_token", "QISKIT_IBM_API_URL": "some_url"}
        with custom_envs(envs):
            service = FakeRuntimeService(auth="cloud", instance=instance)
        self.assertTrue(service._account)
        self.assertEqual(service._account.instance, instance)

    def _verify_prefs(self, prefs, account):
        if "proxies" in prefs:
            self.assertEqual(account.proxies, prefs["proxies"])
        if "verify" in prefs:
            self.assertEqual(account.verify, prefs["verify"])
        if "instance" in prefs:
            self.assertEqual(account.instance, prefs["instance"])
