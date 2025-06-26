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

from typing import Dict, Optional, Any, Callable
from ..proxies import ProxyConfiguration

from ..utils import default_runtime_url_resolver
from ..api.auth import CloudAuth


class ClientParameters:
    """IBM Quantum account client parameters."""

    def __init__(
        self,
        channel: str,
        token: str,
        url: str = None,
        instance: Optional[str] = None,
        proxies: Optional[ProxyConfiguration] = None,
        verify: bool = True,
        private_endpoint: Optional[bool] = False,
        url_resolver: Optional[Callable[[str, str, Optional[bool], str], str]] = None,
    ) -> None:
        """ClientParameters constructor.

        Args:
            channel: Channel type. ``ibm_cloud``, or ``ibm_quantum_platform``.
            token: IBM Quantum Platform API token.
            url: IBM Quantum Platform URL.
            instance: Service instance to use.
            proxies: Proxy configuration.
            verify: If ``False``, ignores SSL certificates errors.
            private_endpoint: Connect to private API URL.
            url_resolver: Function used to resolve the runtime url.
        """
        self.token = token
        self.instance = instance
        self.channel = channel
        self.url = url
        self.proxies = proxies
        self.verify = verify
        self.private_endpoint = private_endpoint
        if not url_resolver:
            url_resolver = default_runtime_url_resolver
        self.url_resolver = url_resolver

    def get_auth_handler(self) -> CloudAuth:
        """Returns the respective authentication handler."""
        return CloudAuth(api_key=self.token, crn=self.instance, private=self.private_endpoint)

    def get_runtime_api_base_url(self) -> str:
        """Returns the Runtime API base url."""
        return self.url_resolver(self.url, self.instance, self.private_endpoint, self.channel)

    def connection_parameters(self) -> Dict[str, Any]:
        """Construct connection related parameters.

        Returns:
            A dictionary with connection-related parameters in the format
            expected by ``requests``. The following keys can be present:
            ``proxies``, ``verify``, and ``auth``.
        """
        request_kwargs: Any = {"verify": self.verify}

        if self.proxies:
            request_kwargs.update(self.proxies.to_request_params())

        return request_kwargs
