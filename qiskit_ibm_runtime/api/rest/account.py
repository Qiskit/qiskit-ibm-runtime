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

"""Account REST adapter."""

import logging
from typing import Dict, Optional, Any, List

from .base import RestAdapterBase
from .backend import Backend
from ..session import RetrySession

logger = logging.getLogger(__name__)


class Account(RestAdapterBase):
    """Rest adapter for hub/group/project related endpoints."""

    URL_MAP = {"backends": "/devices/v/1"}

    TEMPLATE_IBM_HUBS = "/Network/{hub}/Groups/{group}/Projects/{project}"
    """str: Template for creating an IBM Quantum URL with
    hub/group/project information."""

    def __init__(
        self, session: RetrySession, hub: str, group: str, project: str
    ) -> None:
        """Account constructor.

        Args:
            session: Session to be used in the adaptor.
            hub: The hub to use.
            group: The group to use.
            project: The project to use.
        """
        self.url_prefix = self.TEMPLATE_IBM_HUBS.format(
            hub=hub, group=group, project=project
        )
        super().__init__(session, self.url_prefix)

    # Function-specific rest adapters.

    def backend(self, backend_name: str) -> Backend:
        """Return an adapter for the backend.

        Args:
            backend_name: Name of the backend.

        Returns:
            The backend adapter.
        """
        return Backend(self.session, backend_name, self.url_prefix)

    # Client functions.

    def backends(self, timeout: Optional[float] = None) -> List[Dict[str, Any]]:
        """Return a list of backends.

        Args:
            timeout: Number of seconds to wait for the request.

        Returns:
            JSON response.
        """
        url = self.get_url("backends")
        return self.session.get(url, timeout=timeout).json()
