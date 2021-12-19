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

"""Represent IBM Quantum account credentials."""

import re
from typing import Dict, Tuple, Optional, Any

from requests.auth import AuthBase
from requests_ntlm import HttpNtlmAuth

from .hub_group_project_id import HubGroupProjectID
from ..accounts import AccountType
from ..api.auth import LegacyAuth, CloudAuth

REGEX_IBM_HUBS = (
    "(?P<prefix>http[s]://.+/api)"
    "/Hubs/(?P<hub>[^/]+)/Groups/(?P<group>[^/]+)/Projects/(?P<project>[^/]+)"
)
"""str: Regex that matches an IBM Quantum URL with hub information."""

TEMPLATE_IBM_HUBS = "{prefix}/Network/{hub}/Groups/{group}/Projects/{project}"
"""str: Template for creating an IBM Quantum URL with hub/group/project information."""


class Credentials:
    """IBM Quantum account credentials and preferences.

    Note:
        By convention, two credentials that have the same hub, group,
        and project are considered equivalent, regardless of other attributes.
    """

    def __init__(
        self,
        token: str,
        url: str = None,
        auth: Optional[AccountType] = None,
        instance: Optional[str] = None,
        auth_url: Optional[str] = None,
        websockets_url: Optional[str] = None,
        hub: Optional[str] = None,
        group: Optional[str] = None,
        project: Optional[str] = None,
        proxies: Optional[Dict] = None,
        verify: bool = True,
        services: Optional[Dict] = None,
        access_token: Optional[str] = None,
        default_provider: Optional[HubGroupProjectID] = None,
    ) -> None:
        """Credentials constructor.

        Args:
            token: IBM Quantum API token.
            url: IBM Quantum URL (gets replaced with a new-style URL with hub, group, project).
            auth_url: IBM Quantum Auth API URL (always https://auth.quantum-computing.ibm.com/api).
            websockets_url: URL for websocket server.
            hub: The hub to use.
            group: The group to use.
            project: The project to use.
            proxies: Proxy configuration.
            verify: If ``False``, ignores SSL certificates errors.
            services: Additional services for this account.
            access_token: IBM Quantum access token.
            default_provider: Default provider to use.
        """
        self.auth = auth
        self.token = token
        self.instance = instance
        self.access_token = access_token
        (
            self.url,
            self.base_url,
            self.hub,
            self.group,
            self.project,
        ) = _unify_ibm_quantum_url(auth, url, hub, group, project)
        self.auth_url = auth_url or url
        self.websockets_url = websockets_url
        self.proxies = proxies or {}
        self.verify = verify
        self.default_provider = default_provider

        # Initialize additional service URLs.
        services = services or {}
        self.runtime_url = services.get("runtime", None)

    def get_auth_handler(self) -> AuthBase:
        """Returns the respective authentication handler."""
        if self.auth == "cloud":
            return CloudAuth(api_key=self.token, crn=self.instance)

        return LegacyAuth(access_token=self.access_token)

    def is_ibm_quantum(self) -> bool:
        """Return whether the credentials represent an IBM Quantum account."""
        return all([self.hub, self.group, self.project])

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Credentials):
            return False
        return (self.token == other.token) & (self.unique_id() == other.unique_id())

    def unique_id(self) -> HubGroupProjectID:
        """Return a value that uniquely identifies these credentials.

        By convention, two credentials that have the same hub, group,
        and project are considered equivalent.

        Returns:
            A ``HubGroupProjectID`` instance.
        """
        return HubGroupProjectID(self.hub, self.group, self.project)

    def connection_parameters(self) -> Dict[str, Any]:
        """Construct connection related parameters.

        Returns:
            A dictionary with connection-related parameters in the format
            expected by ``requests``. The following keys can be present:
            ``proxies``, ``verify``, and ``auth``.
        """
        request_kwargs = {"verify": self.verify}

        if self.proxies:
            if "urls" in self.proxies:
                request_kwargs["proxies"] = self.proxies["urls"]

            if "username_ntlm" in self.proxies and "password_ntlm" in self.proxies:
                request_kwargs["auth"] = HttpNtlmAuth(
                    self.proxies["username_ntlm"], self.proxies["password_ntlm"]
                )

        return request_kwargs


def _unify_ibm_quantum_url(
    auth: AccountType,
    url: Optional[str] = None,
    hub: Optional[str] = None,
    group: Optional[str] = None,
    project: Optional[str] = None,
) -> Tuple[str, str, Optional[str], Optional[str], Optional[str]]:
    """Return a new-style set of credential values (url and hub parameters).

    Args:
        url: URL for IBM Quantum.
        hub: The hub to use.
        group: The group to use.
        project: The project to use.

    Returns:
        A tuple that consists of ``url``, ``base_url``, ``hub``, ``group``,
        and ``project``, where

            * url: The new-style IBM Quantum URL that contains
              the hub, group, and project names.
            * base_url: Base URL that does not contain the hub, group, and
              project names.
            * hub: The hub to use.
            * group: The group to use.
            * project: The project to use.
    """
    # Check if the URL is "new style", and retrieve embedded parameters from it.
    regex_match = re.match(REGEX_IBM_HUBS, url, re.IGNORECASE)
    base_url = url

    if auth == "cloud":
        base_url = url
    elif regex_match:
        base_url, hub, group, project = regex_match.groups()
    else:
        if hub and group and project:
            # Assume it is an IBM Quantum URL, and update the url.
            url = TEMPLATE_IBM_HUBS.format(
                prefix=url, hub=hub, group=group, project=project
            )
        else:
            # Cleanup the hub, group and project, without modifying the url.
            hub = group = project = None
    return url, base_url, hub, group, project
