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

"""Context managers for using with IBM Provider unit tests."""

import os
import json
import uuid
from contextlib import ContextDecorator
from tempfile import NamedTemporaryFile
from unittest.mock import patch

from qiskit_ibm_runtime.accounts import management
from qiskit_ibm_runtime.accounts.account import CLOUD_API_URL, LEGACY_API_URL
from qiskit_ibm_runtime.credentials.environ import VARIABLES_MAP


CREDENTIAL_ENV_VARS = VARIABLES_MAP.keys()


class custom_envs(ContextDecorator):
    """Context manager that modifies environment variables."""

    # pylint: disable=invalid-name

    def __init__(self, new_environ):
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

    # pylint: disable=invalid-name

    def __init__(self, vars_to_remove):
        """no_envs constructor.

        Args:
            vars_to_remove (list): environment variables to remove.
        """
        self.vars_to_remove = vars_to_remove
        self.os_environ_original = os.environ.copy()

    def __enter__(self):
        # Remove the original variables from `os.environ`.
        modified_environ = {
            key: value
            for key, value in os.environ.items()
            if key not in self.vars_to_remove
        }
        os.environ = modified_environ

    def __exit__(self, *exc):
        os.environ = self.os_environ_original


class no_file(ContextDecorator):
    """Context manager that disallows access to a file."""

    # pylint: disable=invalid-name

    def __init__(self, filename):
        self.filename = filename
        # Store the original `os.path.isfile` function, for mocking.
        self.isfile_original = os.path.isfile
        self.patcher = patch("os.path.isfile", side_effect=self.side_effect)

    def __enter__(self):
        self.patcher.start()

    def __exit__(self, *exc):
        self.patcher.stop()

    def side_effect(self, filename_):
        """Return False for the specified file."""
        if filename_ == self.filename:
            return False
        return self.isfile_original(filename_)


class custom_qiskitrc(ContextDecorator):
    """Context manager that uses a temporary qiskitrc."""

    # pylint: disable=invalid-name

    def __init__(self, contents=None, **kwargs):
        # Create a temporary file with the contents.
        contents = contents or get_qiskitrc_contents(**kwargs)
        self.tmp_file = NamedTemporaryFile(mode="w+")
        json.dump(contents, self.tmp_file)
        self.tmp_file.flush()
        self.default_qiskitrc_file_original = (
            management._DEFAULT_ACCOUNG_CONFIG_JSON_FILE
        )

    def __enter__(self):
        # Temporarily modify the default location of the qiskitrc file.
        management._DEFAULT_ACCOUNG_CONFIG_JSON_FILE = self.tmp_file.name
        return self

    def __exit__(self, *exc):
        # Delete the temporary file and restore the default location.
        self.tmp_file.close()
        management._DEFAULT_ACCOUNG_CONFIG_JSON_FILE = (
            self.default_qiskitrc_file_original
        )


def get_qiskitrc_contents(
    name=None,
    auth="cloud",
    token=None,
    url=None,
    instance=None,
    verify=None,
    proxies=None,
):
    """Generate qiskitrc content"""
    if instance is None:
        instance = "some_instance" if auth == "cloud" else "hub/group/project"
    token = token or uuid.uuid4().hex
    if name is None:
        name = (
            management._DEFAULT_ACCOUNT_NAME_CLOUD
            if auth == "cloud"
            else management._DEFAULT_ACCOUNT_NAME_LEGACY
        )
    if url is None:
        url = CLOUD_API_URL if auth == "cloud" else LEGACY_API_URL
    out = {
        name: {
            "auth": auth,
            "url": url,
            "token": token,
            "instance": instance,
        }
    }
    if verify is not None:
        out["verify"] = verify
    if proxies is not None:
        out["proxies"] = proxies
    return out
