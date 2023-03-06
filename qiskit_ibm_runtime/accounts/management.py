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
import ast
from typing import Optional, Dict
from .exceptions import AccountNotFoundError
from .account import Account, ChannelType
from ..proxies import ProxyConfiguration
from .storage import save_config, read_config, delete_config, read_qiskitrc

_DEFAULT_ACCOUNT_CONFIG_JSON_FILE = os.path.join(
    os.path.expanduser("~"), ".qiskit", "qiskit-ibm.json"
)
_QISKITRC_CONFIG_FILE = os.path.join(os.path.expanduser("~"), ".qiskit", "qiskitrc")
_DEFAULT_ACCOUNT_NAME = "default"
_DEFAULT_ACCOUNT_NAME_LEGACY = "default-legacy"
_DEFAULT_ACCOUNT_NAME_CLOUD = "default-cloud"
_DEFAULT_ACCOUNT_NAME_IBM_QUANTUM = "default-ibm-quantum"
_DEFAULT_ACCOUNT_NAME_IBM_CLOUD = "default-ibm-cloud"
_DEFAULT_CHANNEL_TYPE: ChannelType = "ibm_cloud"
_CHANNEL_TYPES = [_DEFAULT_CHANNEL_TYPE, "ibm_quantum"]


class AccountManager:
    """Class that bundles account management related functionality."""

    @classmethod
    def save(
        cls,
        token: Optional[str] = None,
        url: Optional[str] = None,
        instance: Optional[str] = None,
        channel: Optional[ChannelType] = None,
        filename: Optional[str] = None,
        name: Optional[str] = _DEFAULT_ACCOUNT_NAME,
        proxies: Optional[ProxyConfiguration] = None,
        verify: Optional[bool] = None,
        overwrite: Optional[bool] = False,
    ) -> None:
        """Save account on disk."""
        cls.migrate(filename=filename)
        channel = channel or os.getenv("QISKIT_IBM_CHANNEL") or _DEFAULT_CHANNEL_TYPE
        name = name or cls._get_default_account_name(channel)
        filename = filename if filename else _DEFAULT_ACCOUNT_CONFIG_JSON_FILE
        filename = os.path.expanduser(filename)
        return save_config(
            filename=filename,
            name=name,
            overwrite=overwrite,
            config=Account(
                token=token,
                url=url,
                instance=instance,
                channel=channel,
                proxies=proxies,
                verify=verify,
            )
            # avoid storing invalid accounts
            .validate().to_saved_format(),
        )

    @staticmethod
    def list(
        default: Optional[bool] = None,
        channel: Optional[ChannelType] = None,
        filename: Optional[str] = None,
        name: Optional[str] = None,
    ) -> Dict[str, Account]:
        """List all accounts in a given filename, or in the default account file."""
        filename = filename if filename else _DEFAULT_ACCOUNT_CONFIG_JSON_FILE
        filename = os.path.expanduser(filename)
        AccountManager.migrate(filename)

        def _matching_name(account_name: str) -> bool:
            return name is None or name == account_name

        def _matching_channel(account: Account) -> bool:
            return channel is None or account.channel == channel

        def _matching_default(account_name: str) -> bool:
            default_accounts = [
                _DEFAULT_ACCOUNT_NAME,
                _DEFAULT_ACCOUNT_NAME_IBM_QUANTUM,
                _DEFAULT_ACCOUNT_NAME_IBM_CLOUD,
            ]
            if default is None:
                return True
            elif default is False:
                return account_name not in default_accounts
            else:
                return account_name in default_accounts

        # load all accounts
        all_accounts = map(
            lambda kv: (
                kv[0],
                Account.from_saved_format(kv[1]),
            ),
            read_config(filename=filename).items(),
        )

        # filter based on input parameters
        filtered_accounts = dict(
            list(
                filter(
                    lambda kv: _matching_channel(kv[1])
                    and _matching_default(kv[0])
                    and _matching_name(kv[0]),
                    all_accounts,
                )
            )
        )

        return filtered_accounts

    @classmethod
    def get(
        cls,
        filename: Optional[str] = None,
        name: Optional[str] = None,
        channel: Optional[ChannelType] = None,
    ) -> Optional[Account]:
        """Read account from disk.

        Args:
            filename: Full path of the file from which to get the account.
            name: Account name. Takes precedence if `auth` is also specified.
            channel: Channel type.

        Returns:
            Account information.

        Raises:
            AccountNotFoundError: If the input value cannot be found on disk.
        """
        filename = filename if filename else _DEFAULT_ACCOUNT_CONFIG_JSON_FILE
        filename = os.path.expanduser(filename)
        cls.migrate(filename)
        if name:
            saved_account = read_config(filename=filename, name=name)
            if not saved_account:
                raise AccountNotFoundError(
                    f"Account with the name {name} does not exist on disk."
                )
            return Account.from_saved_format(saved_account)

        channel_ = channel or os.getenv("QISKIT_IBM_CHANNEL") or _DEFAULT_CHANNEL_TYPE
        env_account = cls._from_env_variables(channel_)
        if env_account is not None:
            return env_account

        if channel:
            saved_account = read_config(
                filename=filename,
                name=cls._get_default_account_name(channel=channel),
            )
            if saved_account is None:
                if os.path.isfile(_QISKITRC_CONFIG_FILE):
                    return cls._from_qiskitrc_file()
                raise AccountNotFoundError(f"No default {channel} account saved.")
            return Account.from_saved_format(saved_account)

        all_config = read_config(filename=filename)
        for channel_type in _CHANNEL_TYPES:
            account_name = cls._get_default_account_name(channel=channel_type)
            if account_name in all_config:
                return Account.from_saved_format(all_config[account_name])

        if os.path.isfile(_QISKITRC_CONFIG_FILE):
            return cls._from_qiskitrc_file()

        raise AccountNotFoundError("Unable to find account.")

    @classmethod
    def delete(
        cls,
        filename: Optional[str] = None,
        name: Optional[str] = None,
        channel: Optional[ChannelType] = None,
    ) -> bool:
        """Delete account from disk."""
        filename = filename if filename else _DEFAULT_ACCOUNT_CONFIG_JSON_FILE
        filename = os.path.expanduser(filename)
        cls.migrate(filename=filename)
        name = name or cls._get_default_account_name(channel)
        return delete_config(
            filename=filename,
            name=name,
        )

    @classmethod
    def migrate(cls, filename: Optional[str] = None) -> None:
        """Migrate accounts on disk by removing `auth` and adding `channel`."""
        filename = filename if filename else _DEFAULT_ACCOUNT_CONFIG_JSON_FILE
        filename = os.path.expanduser(filename)
        data = read_config(filename=filename)
        for key, value in data.items():
            if key == _DEFAULT_ACCOUNT_NAME_CLOUD:
                value.pop("auth", None)
                value.update(channel="ibm_cloud")
                delete_config(filename=filename, name=key)
                save_config(
                    filename=filename,
                    name=_DEFAULT_ACCOUNT_NAME_IBM_CLOUD,
                    config=value,
                    overwrite=False,
                )
            elif key == _DEFAULT_ACCOUNT_NAME_LEGACY:
                value.pop("auth", None)
                value.update(channel="ibm_quantum")
                delete_config(filename=filename, name=key)
                save_config(
                    filename=filename,
                    name=_DEFAULT_ACCOUNT_NAME_IBM_QUANTUM,
                    config=value,
                    overwrite=False,
                )
            else:
                if isinstance(value, dict) and "auth" in value:
                    if value["auth"] == "cloud":
                        value.update(channel="ibm_cloud")
                    elif value["auth"] == "legacy":
                        value.update(channel="ibm_quantum")
                    value.pop("auth", None)
                    save_config(
                        filename=filename,
                        name=key,
                        config=value,
                        overwrite=True,
                    )

    @classmethod
    def _from_env_variables(cls, channel: Optional[ChannelType]) -> Optional[Account]:
        """Read account from environment variable."""
        token = os.getenv("QISKIT_IBM_TOKEN")
        url = os.getenv("QISKIT_IBM_URL")
        if not (token and url):
            return None
        return Account(
            token=token,
            url=url,
            instance=os.getenv("QISKIT_IBM_INSTANCE"),
            channel=channel,
        )

    @classmethod
    def _get_default_account_name(cls, channel: ChannelType) -> str:
        return (
            _DEFAULT_ACCOUNT_NAME_IBM_QUANTUM
            if channel == "ibm_quantum"
            else _DEFAULT_ACCOUNT_NAME_IBM_CLOUD
        )

    @classmethod
    def _from_qiskitrc_file(cls) -> Optional[Account]:
        """Read account from qiskitrc file."""
        qiskitrc_data = read_qiskitrc(_QISKITRC_CONFIG_FILE)
        proxies = (
            ProxyConfiguration(ast.literal_eval(qiskitrc_data["proxies"]))
            if "proxies" in qiskitrc_data
            else None
        )
        save_config(
            filename=_DEFAULT_ACCOUNT_CONFIG_JSON_FILE,
            name=_DEFAULT_ACCOUNT_NAME_IBM_QUANTUM,
            overwrite=False,
            config=Account(
                token=qiskitrc_data.get("token", None),
                url=qiskitrc_data.get("url", None),
                instance=qiskitrc_data.get("default_provider", None),
                verify=bool(qiskitrc_data.get("verify", None)),
                proxies=proxies,
                channel="ibm_quantum",
            )
            .validate()
            .to_saved_format(),
        )
        default_config = read_config(filename=_DEFAULT_ACCOUNT_CONFIG_JSON_FILE)
        return Account.from_saved_format(
            default_config[_DEFAULT_ACCOUNT_NAME_IBM_QUANTUM]
        )
