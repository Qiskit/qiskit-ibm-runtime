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

"""Context managers for using with IBM Provider unit tests."""

import json
import os
import uuid
from contextlib import ContextDecorator
from tempfile import NamedTemporaryFile
from typing import Any

from qiskit_ibm_runtime.accounts import management
from qiskit_ibm_runtime.accounts.account import IBM_QUANTUM_PLATFORM_API_URL


class custom_envs(ContextDecorator):
    """Context manager that modifies environment variables."""

    def __init__(self, new_environ: dict):
        """custom_envs constructor.

        Args:
            new_environ (dict): a dictionary of new environment variables to
                use.
        """
        self.new_environ = new_environ
        self.os_environ_original = os.environ.copy()

    def __enter__(self):
        # Remove the original variables from `os.environ`.
        modified_environ = {**os.environ, **self.new_environ}
        os.environ = modified_environ

    def __exit__(self, *exc):
        os.environ = self.os_environ_original


class no_envs(ContextDecorator):
    """Context manager that disables environment variables."""

    def __init__(self, vars_to_remove: list[str]):
        """no_envs constructor.

        Args:
            vars_to_remove (list): environment variables to remove.
        """
        self.vars_to_remove = vars_to_remove
        self.os_environ_original = os.environ.copy()

    def __enter__(self):
        # Remove the original variables from `os.environ`.
        modified_environ = {
            key: value for key, value in os.environ.items() if key not in self.vars_to_remove
        }
        os.environ = modified_environ

    def __exit__(self, *exc):
        os.environ = self.os_environ_original


class temporary_account_config_file(ContextDecorator):
    """Context manager that uses a temporary json file."""

    def __init__(self, contents: str | dict | None = None, **kwargs: Any) -> None:
        # Create a temporary file with the contents.
        contents = contents if contents is not None else get_account_config_contents(**kwargs)

        self.tmp_file = NamedTemporaryFile(mode="w+")
        json.dump(contents, self.tmp_file)
        self.tmp_file.flush()
        self.account_config_json_backup = management._DEFAULT_ACCOUNT_CONFIG_JSON_FILE

    def __enter__(self):
        # Temporarily modify the default location of the configuration file.
        management._DEFAULT_ACCOUNT_CONFIG_JSON_FILE = self.tmp_file.name
        return self

    def __exit__(self, *exc):
        # Delete the temporary file and restore the default location.
        self.tmp_file.close()
        management._DEFAULT_ACCOUNT_CONFIG_JSON_FILE = self.account_config_json_backup


def get_account_config_contents(
    name: str | None = None,
    channel: str = "ibm_quantum_platform",
    token: str | None = None,
    url: str | None = None,
    instance: str | None = None,
    verify: bool | None = None,
    proxies: dict | None = None,
    set_default: bool | None = None,
) -> dict:
    """Generate account config file content."""
    token = token or uuid.uuid4().hex
    if name is None:
        name = (
            management._DEFAULT_ACCOUNT_NAME_IBM_CLOUD
            if channel == "ibm_cloud"
            else (management._DEFAULT_ACCOUNT_NAME_IBM_QUANTUM_PLATFORM)
        )
    if url is None:
        url = IBM_QUANTUM_PLATFORM_API_URL
    out: dict[str, Any] = {
        name: {
            "channel": channel,
            "url": url,
            "token": token,
            "instance": instance,
        }
    }
    if verify is not None:
        out[name]["verify"] = verify
    if proxies is not None:
        out[name]["proxies"] = proxies
    if set_default:
        out[name]["is_default_account"] = True
    return out
