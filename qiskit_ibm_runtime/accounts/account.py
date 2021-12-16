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

"""Account related classes and functions."""


from typing import Optional
from urllib.parse import urlparse

from typing_extensions import Literal

AccountType = Optional[Literal["cloud", "legacy"]]

LEGACY_API_URL = "https://auth.quantum-computing.ibm.com/api"
CLOUD_API_URL = "https://cloud.ibm.com"


def _assert_valid_auth(auth: AccountType) -> None:
    """Assert that the auth parameter is valid."""
    if not (auth in ["cloud", "legacy"]):
        raise ValueError(
            f"Inappropriate `auth` value. Expected one of ['cloud', 'legacy'], got '{auth}'."
        )


def _assert_valid_token(token: str) -> None:
    """Assert that the token is valid."""
    if not (isinstance(token, str) and len(token) > 0):
        raise ValueError(
            f"Inappropriate `token` value. Expected a non-empty string, got '{token}'."
        )


def _assert_valid_url(url: str) -> None:
    """Assert that the URL is valid."""
    try:
        urlparse(url)
    except:
        raise ValueError(f"Inappropriate `url` value. Failed to parse '{url}' as URL.")


def _assert_valid_instance(auth: AccountType, instance: str) -> None:
    """Assert that the instance name is valid for the given account type."""
    if auth == "cloud":
        if not (isinstance(instance, str) and len(instance) > 0):
            raise ValueError(
                f"Inappropriate `instance` value. Expected a non-empty string."
            )
    # TODO: add validation for legacy instance when adding test coverage


class Account:
    """Class that represents an account."""

    def __init__(
        self,
        auth: AccountType,
        token: str,
        url: Optional[str],
        instance: Optional[str] = None,
        # TODO: add validation for proxies input format
        proxies: Optional[dict] = None,
        verify: Optional[bool] = True,
    ):
        """Account constructor."""
        _assert_valid_auth(auth)
        self.auth = auth

        _assert_valid_token(token)
        self.token = token

        resolved_url = url or LEGACY_API_URL if auth == "legacy" else CLOUD_API_URL
        _assert_valid_url(resolved_url)
        self.url = resolved_url

        _assert_valid_instance(auth, instance)
        self.instance = instance
        self.proxies = proxies
        self.verify = verify

    def to_saved_format(self) -> dict:
        """Returns a dictionary that represents how the account is saved on disk."""
        return {k: v for k, v in self.__dict__.items() if v is not None}

    @classmethod
    def from_saved_format(cls, data: dict) -> "Account":
        """Creates an account instance from data saved on disk."""
        return cls(
            auth=data.get("auth"),
            url=data.get("url"),
            token=data.get("token"),
            instance=data.get("instance"),
            proxies=data.get("proxies"),
            verify=data.get("verify"),
        )
