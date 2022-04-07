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

"""Fake ibm_quantum AuthClient."""

from typing import Dict, List, Union, Optional


class BaseFakeAuthClient:
    """Base class for faking the runtime client."""

    def __init__(self, *args, **kwargs):
        """Initialize a auth runtime client."""
        pass

    def user_urls(self) -> Dict[str, Union[str, Dict]]:
        """Retrieve the API URLs from the authentication service.

        Returns:
            A dict with the base URLs for the services. Currently
            supported keys are:

                * ``http``: The API URL for HTTP communication.
                * ``ws``: The API URL for websocket communication.
                * ``services`: The API URL for additional services.
        """
        return {
            "http": "http://127.0.0.1",
            "ws": "ws://127.0.0.1",
            "services": {"runtime": "http://127.0.0.1"},
        }

    def user_hubs(self) -> List[Dict[str, str]]:
        """Retrieve the hub/group/project sets available to the user."""

        hubs = []
        for idx in range(2):
            hubs.append(
                {"hub": f"hub{idx}", "group": f"group{idx}", "project": f"project{idx}"}
            )
        return hubs

    def api_version(self) -> Dict[str, Union[str, bool]]:
        """Return the version of the API.

        Returns:
            API version.
        """
        return {"new_api": True, "api-auth": "0.1"}

    def current_access_token(self) -> Optional[str]:
        """Return the current access token.

        Returns:
            The access token in use.
        """
        return "123"

    def current_service_urls(self) -> Dict[str, str]:
        """Return the current service URLs.

        Returns:
            A dict with the base URLs for the services, in the same
            format as :meth:`user_urls()`.
        """
        return {"runtime": "http://127.0.0.1"}
