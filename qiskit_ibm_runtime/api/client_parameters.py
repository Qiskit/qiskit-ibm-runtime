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

"""Represent IBM Quantum account client parameters."""

from typing import Dict, Optional, Any, Union

from requests_ntlm import HttpNtlmAuth

from ..api.auth import LegacyAuth, CloudAuth

TEMPLATE_IBM_HUBS = "{prefix}/Network/{hub}/Groups/{group}/Projects/{project}"
"""str: Template for creating an IBM Quantum URL with hub/group/project information."""


class ClientParameters:
    """IBM Quantum account client parameters."""

    def __init__(
        self,
        auth_type: str,
        token: str,
        url: str = None,
        instance: Optional[str] = None,
        proxies: Optional[Dict] = None,
        verify: bool = True,
    ) -> None:
        """ClientParameters constructor.

        Args:
            token: IBM Quantum API token.
            url: IBM Quantum URL (gets replaced with a new-style URL with hub, group, project).
            proxies: Proxy configuration.
            verify: If ``False``, ignores SSL certificates errors.
        """
        self.token = token
        self.instance = instance
        self.auth_type = auth_type
        self.url = url
        self.proxies = proxies
        self.verify = verify

    def get_auth_handler(self) -> Union[CloudAuth, LegacyAuth]:
        """Returns the respective authentication handler."""
        if self.auth_type == "cloud":
            return CloudAuth(api_key=self.token, crn=self.instance)

        return LegacyAuth(access_token=self.token)

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
