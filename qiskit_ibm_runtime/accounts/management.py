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

from .account import Account
from .storage import save_config, read_config, delete_config

_DEFAULT_ACCOUNG_CONFIG_JSON_FILE = os.path.join(
    os.path.expanduser("~"), ".qiskit", "qiskit-ibm.json"
)
_DEFAULT_ACCOUNT_NAME = "default"


class AccountManager:
    """Class that bundles account management related functionality."""

    @staticmethod
    def save(account: Account, name: Optional[str] = _DEFAULT_ACCOUNT_NAME) -> None:
        """Save account on disk."""

        return save_config(
            filename=_DEFAULT_ACCOUNG_CONFIG_JSON_FILE,
            name=name,
            config=account.to_saved_format(),
        )

    @staticmethod
    def list() -> Union[dict, None]:
        """List all accounts saved on disk."""

        return read_config(filename=_DEFAULT_ACCOUNG_CONFIG_JSON_FILE)

    @staticmethod
    def get(name: Optional[str] = _DEFAULT_ACCOUNT_NAME) -> Account:
        """Read account from disk."""
        return Account.from_saved_format(
            read_config(filename=_DEFAULT_ACCOUNG_CONFIG_JSON_FILE, name=name)
        )

    @staticmethod
    def delete(name: Optional[str] = _DEFAULT_ACCOUNT_NAME) -> bool:
        """Read account from disk."""
        return delete_config(name=name, filename=_DEFAULT_ACCOUNG_CONFIG_JSON_FILE)
