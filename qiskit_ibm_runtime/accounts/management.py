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

"""Account management related classes and functions."""

import os
from typing import Optional, Dict
from .exceptions import AccountNotFoundError
from .account import Account, AccountType
from ..proxies import ProxyConfiguration
from .storage import save_config, read_config, delete_config

_DEFAULT_ACCOUNT_CONFIG_JSON_FILE = os.path.join(
    os.path.expanduser("~"), ".qiskit", "qiskit-ibm.json"
)
_DEFAULT_ACCOUNT_NAME = "default"
_DEFAULT_ACCOUNT_NAME_LEGACY = "default-legacy"
_DEFAULT_ACCOUNT_NAME_CLOUD = "default-cloud"
_DEFAULT_ACCOUNT_TYPE: AccountType = "cloud"
_ACCOUNT_TYPES = [_DEFAULT_ACCOUNT_TYPE, "legacy"]


class AccountManager:
    """Class that bundles account management related functionality."""

    @classmethod
    def save(
        cls,
        token: Optional[str] = None,
        url: Optional[str] = None,
        instance: Optional[str] = None,
        auth: Optional[AccountType] = None,
        name: Optional[str] = _DEFAULT_ACCOUNT_NAME,
        proxies: Optional[ProxyConfiguration] = None,
        verify: Optional[bool] = None,
        overwrite: Optional[bool] = False,
    ) -> None:
        """Save account on disk."""
        config_key = name or cls._get_default_account_name(auth)
        return save_config(
            filename=_DEFAULT_ACCOUNT_CONFIG_JSON_FILE,
            name=config_key,
            overwrite=overwrite,
            config=Account(
                token=token,
                url=url,
                instance=instance,
                auth=auth,
                proxies=proxies,
                verify=verify,
            )
            # avoid storing invalid accounts
            .validate().to_saved_format(),
        )

    @staticmethod
    def list(
        default: Optional[bool] = None,
        auth: Optional[str] = None,
        name: Optional[str] = None,
    ) -> Dict[str, Account]:
        """List all accounts saved on disk."""

        def _matching_name(account_name: str) -> bool:
            return name is None or name == account_name

        def _matching_auth(account: Account) -> bool:
            return auth is None or account.auth == auth

        def _matching_default(account_name: str) -> bool:
            default_accounts = [
                _DEFAULT_ACCOUNT_NAME,
                _DEFAULT_ACCOUNT_NAME_LEGACY,
                _DEFAULT_ACCOUNT_NAME_CLOUD,
            ]
            if default is None:
                return True
            elif default is False:
                return account_name not in default_accounts
            else:
                return account_name in default_accounts

        # load all accounts
        all_accounts = map(
            lambda kv: (kv[0], Account.from_saved_format(kv[1])),
            read_config(filename=_DEFAULT_ACCOUNT_CONFIG_JSON_FILE).items(),
        )

        # filter based on input parameters
        filtered_accounts = dict(
            list(
                filter(
                    lambda kv: _matching_auth(kv[1])
                    and _matching_default(kv[0])
                    and _matching_name(kv[0]),
                    all_accounts,
                )
            )
        )

        return filtered_accounts

    @classmethod
    def get(
        cls, name: Optional[str] = None, auth: Optional[AccountType] = None
    ) -> Optional[Account]:
        """Read account from disk.

        Args:
            name: Account name. Takes precedence if `auth` is also specified.
            auth: Account auth type.

        Returns:
            Account information.

        Raises:
            AccountNotFoundError: If the input value cannot be found on disk.
        """
        if name:
            saved_account = read_config(
                filename=_DEFAULT_ACCOUNT_CONFIG_JSON_FILE, name=name
            )
            if not saved_account:
                raise AccountNotFoundError(
                    f"Account with the name {name} does not exist on disk."
                )
            return Account.from_saved_format(saved_account)

        auth_ = auth or _DEFAULT_ACCOUNT_TYPE
        env_account = cls._from_env_variables(auth_)
        if env_account is not None:
            return env_account

        if auth:
            saved_account = read_config(
                filename=_DEFAULT_ACCOUNT_CONFIG_JSON_FILE,
                name=cls._get_default_account_name(auth),
            )
            if saved_account is None:
                raise AccountNotFoundError(f"No default {auth} account saved.")
            return Account.from_saved_format(saved_account)

        all_config = read_config(filename=_DEFAULT_ACCOUNT_CONFIG_JSON_FILE)
        for account_type in _ACCOUNT_TYPES:
            account_name = cls._get_default_account_name(account_type)
            if account_name in all_config:
                return Account.from_saved_format(all_config[account_name])

        raise AccountNotFoundError("Unable to find account.")

    @classmethod
    def delete(
        cls,
        name: Optional[str] = None,
        auth: Optional[str] = None,
    ) -> bool:
        """Delete account from disk."""

        config_key = name or cls._get_default_account_name(auth)
        return delete_config(
            name=config_key, filename=_DEFAULT_ACCOUNT_CONFIG_JSON_FILE
        )

    @classmethod
    def _from_env_variables(cls, auth: Optional[AccountType]) -> Optional[Account]:
        """Read account from environment variable."""
        token = os.getenv("QISKIT_IBM_TOKEN")
        url = os.getenv("QISKIT_IBM_URL")
        if not (token and url):
            return None
        return Account(
            token=token, url=url, instance=os.getenv("QISKIT_IBM_INSTANCE"), auth=auth
        )

    @classmethod
    def _get_default_account_name(cls, auth: AccountType) -> str:
        return (
            _DEFAULT_ACCOUNT_NAME_LEGACY
            if auth == "legacy"
            else _DEFAULT_ACCOUNT_NAME_CLOUD
        )
