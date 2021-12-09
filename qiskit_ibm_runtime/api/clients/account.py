# This code is part of Qiskit.
#
# (C) Copyright IBM 2018, 2020.
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
from datetime import datetime

from qiskit_ibm_runtime.credentials import Credentials

from ..rest import Api, Account
from ..rest.backend import Backend
from ..session import RetrySession
from .base import BaseClient

logger = logging.getLogger(__name__)


class AccountClient(BaseClient):
    """Client for accessing an individual IBM Quantum account."""

    def __init__(self, credentials: Credentials, **request_kwargs: Any) -> None:
        """AccountClient constructor.

        Args:
            credentials: Account credentials.
            **request_kwargs: Arguments for the request ``Session``.
        """
        self._session = RetrySession(
            credentials.base_url, auth=credentials.get_auth_handler(), **request_kwargs
        )
        # base_api is used to handle endpoints that don't include h/g/p.
        # account_api is for h/g/p.
        self.base_api = Api(self._session)
        self.account_api = Account(
            session=self._session,
            hub=credentials.hub,
            group=credentials.group,
            project=credentials.project,
        )
        self._credentials = credentials

    # Backend-related public functions.

    def list_backends(self, timeout: Optional[float] = None) -> List[Dict[str, Any]]:
        """Return backends available for this provider.

        Args:
            timeout: Number of seconds to wait for the request.

        Returns:
            Backends available for this provider.
        """
        return self.account_api.backends(timeout=timeout)

    def backend_status(self, backend_name: str) -> Dict[str, Any]:
        """Return the status of the backend.

        Args:
            backend_name: The name of the backend.

        Returns:
            Backend status.
        """
        return self.account_api.backend(backend_name).status()

    def backend_properties(
        self, backend_name: str, datetime: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Return the properties of the backend.

        Args:
            backend_name: The name of the backend.
            datetime: Date and time for additional filtering of backend properties.

        Returns:
            Backend properties.
        """
        # pylint: disable=redefined-outer-name
        return self.account_api.backend(backend_name).properties(datetime=datetime)

    def backend_pulse_defaults(self, backend_name: str) -> Dict:
        """Return the pulse defaults of the backend.

        Args:
            backend_name: The name of the backend.

        Returns:
            Backend pulse defaults.
        """
        return self.account_api.backend(backend_name).pulse_defaults()

    def backend_job_limit(self, backend_name: str) -> Dict[str, Any]:
        """Return the job limit for the backend.

        Args:
            backend_name: The name of the backend.

        Returns:
            Backend job limit.
        """
        return self.account_api.backend(backend_name).job_limit()

    def backend_reservations(
        self,
        backend_name: str,
        start_datetime: Optional[datetime] = None,
        end_datetime: Optional[datetime] = None,
    ) -> List:
        """Return backend reservation information.

        Args:
            backend_name: Name of the backend.
            start_datetime: Starting datetime in UTC.
            end_datetime: Ending datetime in UTC.

        Returns:
            Backend reservation information.
        """
        backend_api = Backend(self._session, backend_name, "/Network")
        return backend_api.reservations(start_datetime, end_datetime)

    def my_reservations(self) -> List:
        """Return backend reservations made by the caller.

        Returns:
            Backend reservation information.
        """
        return self.base_api.reservations()
