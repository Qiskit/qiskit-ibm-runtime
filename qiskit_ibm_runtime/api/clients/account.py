# This code is part of Qiskit.
#
# (C) Copyright IBM 2018, 2021.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Client for accessing an individual IBM Quantum account."""

import logging

from typing import List, Dict, Any, Optional
from datetime import datetime as python_datetime

from qiskit_ibm_runtime.utils.hgp import from_instance_format

from .backend import BaseBackendClient
from ..rest import Account
from ..session import RetrySession
from ..client_parameters import ClientParameters

logger = logging.getLogger(__name__)


class AccountClient(BaseBackendClient):
    """Client for accessing an individual IBM Quantum account."""

    def __init__(self, params: ClientParameters) -> None:
        """AccountClient constructor.

        Args:
            params: Parameters used for server connection.
        """
        self._session = RetrySession(
            params.url, auth=params.get_auth_handler(), **params.connection_parameters()
        )
        hub, group, project = from_instance_format(params.instance)
        self.account_api = Account(
            session=self._session,
            hub=hub,
            group=group,
            project=project,
        )

    def list_backends(self) -> List[Dict[str, Any]]:
        """Return backends available.

        Returns:
            Backends available for this hub/group/project.
        """
        return self.account_api.backends()

    def backend_status(self, backend_name: str) -> Dict[str, Any]:
        """Return the status of the backend.

        Args:
            backend_name: The name of the backend.

        Returns:
            Backend status.
        """
        return self.account_api.backend(backend_name).status()

    def backend_properties(
        self, backend_name: str, datetime: Optional[python_datetime] = None
    ) -> Dict[str, Any]:
        """Return the properties of the backend.

        Args:
            backend_name: The name of the backend.
            datetime: Date and time for additional filtering of backend properties.

        Returns:
            Backend properties.
        """
        return self.account_api.backend(backend_name).properties(datetime=datetime)

    def backend_pulse_defaults(self, backend_name: str) -> Dict:
        """Return the pulse defaults of the backend.

        Args:
            backend_name: The name of the backend.

        Returns:
            Backend pulse defaults.
        """
        return self.account_api.backend(backend_name).pulse_defaults()
