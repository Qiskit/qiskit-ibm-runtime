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
from typing import Optional

from .account import Account, AccountType
from .storage import save_config, read_config, delete_config

_DEFAULT_ACCOUNG_CONFIG_JSON_FILE = os.path.join(
    os.path.expanduser("~"), ".qiskit", "qiskit-ibm.json"
)
_DEFAULT_ACCOUNT_NAME_LEGACY = "default-legacy"
_DEFAULT_ACCOUNT_NAME_CLOUD = "default-cloud"
_DEFAULT_ACCOUNT_TYPE: AccountType = "cloud"


class AccountManager:
    """Class that bundles account management related functionality."""

    @staticmethod
    def save(account: Account, name: Optional[str] = None) -> None:
        """Save account on disk."""
        config_key = name or _get_default_account_name(account.auth)
        return save_config(
            filename=_DEFAULT_ACCOUNG_CONFIG_JSON_FILE,
            name=config_key,
            config=account.to_saved_format(),
        )

    @staticmethod
    def list(
        default: Optional[bool] = None, auth: Optional[str] = None
    ) -> dict[str, Account]:
        """List all accounts saved on disk by name."""
        return dict(
            filter(
                lambda input: input[1],
                map(
                    lambda kv: (kv[0], Account.from_saved_format(kv[1])),
                    read_config(filename=_DEFAULT_ACCOUNG_CONFIG_JSON_FILE).items(),
                ),
            ),
        )

    @staticmethod
    def get(
        name: Optional[str] = None, auth: Optional[str] = _DEFAULT_ACCOUNT_TYPE
    ) -> Account:
        """Read account from disk."""
        config_key = name or _get_default_account_name(auth)
        return Account.from_saved_format(
            read_config(filename=_DEFAULT_ACCOUNG_CONFIG_JSON_FILE, name=config_key)
        )

    @staticmethod
    def delete(
        name: Optional[str] = None, auth: Optional[str] = _DEFAULT_ACCOUNT_TYPE
    ) -> bool:
        """Delete account from disk."""
        config_key = name or _get_default_account_name(auth)
        return delete_config(
            name=config_key, filename=_DEFAULT_ACCOUNG_CONFIG_JSON_FILE
        )


def _get_default_account_name(auth: AccountType):
    return (
        _DEFAULT_ACCOUNT_NAME_CLOUD if auth == "cloud" else _DEFAULT_ACCOUNT_NAME_LEGACY
    )
