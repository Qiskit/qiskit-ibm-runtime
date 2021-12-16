import json
from contextlib import ContextDecorator
from tempfile import NamedTemporaryFile
from typing import Optional, List
from unittest import TestCase

from qiskit_ibm_runtime.accounts import AccountManager, Account
from qiskit_ibm_runtime.accounts import management
from ..ibm_test_case import IBMTestCase

_TEST_LEGACY_ACCOUNT = Account(
    "legacy",
    "token-x",
    "https://auth.quantum-computing.ibm.com/api",
    "ibm-q/open/main",
)

_TEST_CLOUD_ACCOUNT = Account(
    auth="cloud",
    token="token-y",
    url="https://cloud.ibm.com",
    instance="crn:v1:bluemix:public:quantum-computing:us-east:a/...::",
)


class temporary_account_config_file(ContextDecorator):
    """Context manager that uses a temporary account configuration file for test purposes."""

    def __init__(self, contents: Optional[str] = "{}"):
        # Create a temporary file with provided contents.
        self.tmp_file = NamedTemporaryFile(mode="w")
        self.tmp_file.write(contents)
        self.tmp_file.flush()
        self.account_config_json_backup = management._DEFAULT_ACCOUNG_CONFIG_JSON_FILE

    def __enter__(self):
        # Temporarily modify the default location of the configuration file.
        management._DEFAULT_ACCOUNG_CONFIG_JSON_FILE = self.tmp_file.name
        return self

    def __exit__(self, *exc):
        # Delete the temporary file and restore the default location.
        self.tmp_file.close()
        management._DEFAULT_ACCOUNG_CONFIG_JSON_FILE = self.account_config_json_backup


class TestAccount(TestCase):
    def test_init(self):
        inputs = [("auth")]
        a = ""


class TestAccountManager(IBMTestCase, TestCase):
    @temporary_account_config_file()
    def test_save_get(self):

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
                AccountManager.save(account=account, name=name_save)
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
        with temporary_account_config_file(
            contents=json.dumps(
                {
                    "key1": _TEST_CLOUD_ACCOUNT.to_saved_format(),
                    "key2": _TEST_LEGACY_ACCOUNT.to_saved_format(),
                }
            )
        ), self.subTest("non-empty list of accounts and filtering"):
            accounts = AccountManager.list()
            self.assertEqual(len(accounts), 2)
            self.assertEqual(accounts["key1"], _TEST_CLOUD_ACCOUNT)
            self.assertTrue(accounts["key2"], _TEST_LEGACY_ACCOUNT)

        with temporary_account_config_file(), self.subTest("empty list of accounts"):
            self.assertEqual(len(AccountManager.list()), 0)

    @temporary_account_config_file(
        contents=json.dumps(
            {
                "key1": _TEST_CLOUD_ACCOUNT.to_saved_format(),
                management._DEFAULT_ACCOUNT_NAME_LEGACY: _TEST_LEGACY_ACCOUNT.to_saved_format(),
                management._DEFAULT_ACCOUNT_NAME_CLOUD: _TEST_CLOUD_ACCOUNT.to_saved_format(),
            }
        )
    )
    def test_delete(self):
        with self.subTest("delete named account"):
            self.assertTrue(AccountManager.delete(name="key1"))
            self.assertFalse(AccountManager.delete(name="key1"))

        with self.subTest("delete default legacy account"):
            self.assertTrue(AccountManager.delete(auth="legacy"))

        with self.subTest("delete default cloud account"):
            self.assertTrue(AccountManager.delete())

        self.assertEquals(len(AccountManager.list()), 0)
