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
from typing import Optional, Union

from .account import Account, AccountType
from .storage import save_config, read_config, delete_config

_DEFAULT_ACCOUNG_CONFIG_JSON_FILE = os.path.join(
    os.path.expanduser("~"), ".qiskit", "qiskit-ibm.json"
)
_DEFAULT_ACCOUNT_NAME = "default"
_DEFAULT_ACCOUNT_NAME_LEGACY = "default-legacy"
_DEFAULT_ACCOUNT_NAME_CLOUD = "default-cloud"
_DEFAULT_ACCOUNT_TYPE: AccountType = "cloud"
_ACCOUNT_TYPES = [_DEFAULT_ACCOUNT_TYPE, "legacy"]


class AccountManager:
    """Class that bundles account management related functionality."""

    @staticmethod
    def save(
        token: Optional[str] = None,
        url: Optional[str] = None,
        instance: Optional[str] = None,
        auth: Optional[AccountType] = None,
        name: Optional[str] = _DEFAULT_ACCOUNT_NAME,
        proxies: Optional[dict] = None,
        verify: Optional[bool] = None,
    ) -> None:
        """Save account on disk."""

        return save_config(
            filename=_DEFAULT_ACCOUNG_CONFIG_JSON_FILE,
            name=name,
            config=Account(
                token=token,
                url=url,
                instance=instance,
                auth=auth,
                proxies=proxies,
                verify=verify,
            ).to_saved_format(),
        )

    @staticmethod
    def list() -> Union[dict, None]:
        """List all accounts saved on disk."""

        return read_config(filename=_DEFAULT_ACCOUNG_CONFIG_JSON_FILE)

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
            ValueError: If the input value cannot be found on disk.
        """
        if name:
            saved_account = read_config(
                filename=_DEFAULT_ACCOUNG_CONFIG_JSON_FILE, name=name
            )
            if not saved_account:
                raise ValueError(
                    f"Account with the name {name} does not exist on disk."
                )
            return Account.from_saved_format(saved_account)

        auth_ = auth or _DEFAULT_ACCOUNT_TYPE
        env_account = cls._from_env_variables(auth_)
        if env_account is not None:
            return env_account

        if auth:
            saved_account = read_config(
                filename=_DEFAULT_ACCOUNG_CONFIG_JSON_FILE,
                name=cls._get_default_account_name(auth),
            )
            if saved_account is None:
                raise ValueError(f"No default {auth} account saved.")
            return Account.from_saved_format(saved_account)

        all_config = read_config(filename=_DEFAULT_ACCOUNG_CONFIG_JSON_FILE)
        for account_type in _ACCOUNT_TYPES:
            account_name = cls._get_default_account_name(account_type)
            if account_name in all_config:
                return Account.from_saved_format(all_config[account_name])

        return None

    @staticmethod
    def delete(name: Optional[str] = _DEFAULT_ACCOUNT_NAME) -> bool:
        """Delete account from disk."""
        return delete_config(name=name, filename=_DEFAULT_ACCOUNG_CONFIG_JSON_FILE)

    @classmethod
    def _from_env_variables(cls, auth: Optional[AccountType]) -> Optional[Account]:
        """Read account from environment variable."""
        token = os.getenv("QISKIT_IBM_API_TOKEN")
        url = os.getenv("QISKIT_IBM_API_URL")
        if not (token and url):
            return None
        return Account(
            token=token, url=url, instance=os.getenv("QISKIT_IBM_INSTANCE"), auth=auth
        )

    @classmethod
    def _get_default_account_name(cls, auth: AccountType) -> str:
        return (
            _DEFAULT_ACCOUNT_NAME_CLOUD
            if auth == "cloud"
            else _DEFAULT_ACCOUNT_NAME_LEGACY
        )
