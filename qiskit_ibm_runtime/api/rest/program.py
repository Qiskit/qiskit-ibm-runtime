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

"""Program REST adapter."""

from typing import Dict, Any, Optional
from concurrent import futures

from .base import RestAdapterBase
from ..session import RetrySession


class Program(RestAdapterBase):
    """Rest adapter for program related endpoints."""

    URL_MAP = {
        "self": "",
        "data": "/data",
        "run": "/jobs",
        "private": "/private",
        "public": "/public",
    }

    _executor = futures.ThreadPoolExecutor()

    def __init__(
        self, session: RetrySession, program_id: str, url_prefix: str = ""
    ) -> None:
        """Job constructor.

        Args:
            session: Session to be used in the adapter.
            program_id: ID of the runtime program.
            url_prefix: Prefix to use in the URL.
        """
        super().__init__(session, "{}/programs/{}".format(url_prefix, program_id))

    def get(self) -> Dict[str, Any]:
        """Return program information.

        Returns:
            JSON response.
        """
        url = self.get_url("self")
        return self.session.get(url).json()

    def make_public(self) -> None:
        """Sets a runtime program's visibility to public."""
        url = self.get_url("public")
        self.session.put(url)

    def make_private(self) -> None:
        """Sets a runtime program's visibility to private."""
        url = self.get_url("private")
        self.session.put(url)

    def delete(self) -> None:
        """Delete this program."""
        url = self.get_url("self")
        self.session.delete(url)

    def update_data(self, program_data: str) -> None:
        """Update program data.

        Args:
            program_data: Program data (base64 encoded).
        """
        url = self.get_url("data")
        self.session.put(
            url, data=program_data, headers={"Content-Type": "application/octet-stream"}
        )

    def update_metadata(
        self,
        name: str = None,
        description: str = None,
        max_execution_time: int = None,
        spec: Optional[Dict] = None,
    ) -> None:
        """Update program metadata.

        Args:
            name: Name of the program.
            description: Program description.
            max_execution_time: Maximum execution time.
            spec: Backend requirements, parameters, interim results, return values, etc.
        """
        url = self.get_url("self")
        payload: Dict = {}
        if name:
            payload["name"] = name
        if description:
            payload["description"] = description
        if max_execution_time:
            payload["cost"] = max_execution_time
        if spec:
            payload["spec"] = spec

        self.session.patch(url, json=payload)
