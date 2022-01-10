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

from requests.auth import AuthBase
from typing_extensions import Literal
from ..proxies import ProxyConfiguration
from ..utils.hgp import from_instance_format
from ..api.auth import LegacyAuth, CloudAuth

AccountType = Optional[Literal["cloud", "legacy"]]

LEGACY_API_URL = "https://auth.quantum-computing.ibm.com/api"
CLOUD_API_URL = "https://us-east.quantum-computing.cloud.ibm.com"


def _assert_valid_auth(auth: AccountType) -> None:
    """Assert that the auth parameter is valid."""
    if not (auth in ["cloud", "legacy"]):
        raise ValueError(
            f"Invalid `auth` value. Expected one of ['cloud', 'legacy'], got '{auth}'."
        )


def _assert_valid_token(token: str) -> None:
    """Assert that the token is valid."""
    if not (isinstance(token, str) and len(token) > 0):
        raise ValueError(
            f"Invalid `token` value. Expected a non-empty string, got '{token}'."
        )


def _assert_valid_url(url: str) -> None:
    """Assert that the URL is valid."""
    try:
        urlparse(url)
    except:
        raise ValueError(f"Invalid `url` value. Failed to parse '{url}' as URL.")


def _assert_valid_proxies(config: ProxyConfiguration) -> None:
    """Assert that the proxy configuration is valid."""
    if config is not None:
        config.validate()


def _assert_valid_instance(auth: AccountType, instance: str) -> None:
    """Assert that the instance name is valid for the given account type."""
    if auth == "cloud":
        if not (isinstance(instance, str) and len(instance) > 0):
            raise ValueError(
                f"Invalid `instance` value. Expected a non-empty string, got '{instance}'."
            )
    if auth == "legacy":
        if instance is not None:
            try:
                from_instance_format(instance)
            except:
                raise ValueError(
                    f"Invalid `instance` value. Expected hub/group/project format, got {instance}"
                )


class Account:
    """Class that represents an account."""

    def __init__(
        self,
        auth: AccountType,
        token: str,
        url: Optional[str] = None,
        instance: Optional[str] = None,
        proxies: Optional[ProxyConfiguration] = None,
        verify: Optional[bool] = True,
    ):
        """Account constructor.

        Args:
            auth: Authentication type, ``cloud`` or ``legacy``.
            token: Account token to use.
            url: Authentication URL.
            instance: Service instance to use.
            proxies: Proxy configuration.
            verify: Whether to verify server's TLS certificate.
        """
        _assert_valid_auth(auth)
        self.auth = auth

        _assert_valid_token(token)
        self.token = token

        resolved_url = url or (LEGACY_API_URL if auth == "legacy" else CLOUD_API_URL)
        _assert_valid_url(resolved_url)
        self.url = resolved_url

        _assert_valid_instance(auth, instance)
        self.instance = instance

        _assert_valid_proxies(proxies)
        self.proxies = proxies

        self.verify = verify

    def to_saved_format(self) -> dict:
        """Returns a dictionary that represents how the account is saved on disk."""
        result = {k: v for k, v in self.__dict__.items() if v is not None}
        if self.proxies:
            result["proxies"] = self.proxies.to_dict()
        return result

    @classmethod
    def from_saved_format(cls, data: dict) -> "Account":
        """Creates an account instance from data saved on disk."""
        proxies = data.get("proxies")
        return cls(
            auth=data.get("auth"),
            url=data.get("url"),
            token=data.get("token"),
            instance=data.get("instance"),
            proxies=ProxyConfiguration(**proxies) if proxies else None,
            verify=data.get("verify", True),
        )

    def get_auth_handler(self) -> AuthBase:
        """Returns the respective authentication handler."""
        if self.auth == "cloud":
            return CloudAuth(api_key=self.token, crn=self.instance)

        return LegacyAuth(access_token=self.token)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Account):
            return False
        return all(
            [
                self.auth == other.auth,
                self.token == other.token,
                self.url == other.url,
                self.instance == other.instance,
                self.proxies == other.proxies,
                self.verify == other.verify,
            ]
        )
