# This code is part of Qiskit.
#
# (C) Copyright IBM 2021-2026.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Root REST adapter."""

import logging
from typing import Any

from .base import RestAdapterBase
from .program_job import ProgramJob

logger = logging.getLogger(__name__)


class Api(RestAdapterBase):
    """Rest adapter for general endpoints."""

    URL_MAP = {
        "login": "/users/loginWithToken",
        "user_info": "/users/me",
        "version": "/version",
        "bookings": "/Network/bookings/v2",
    }

    def job(self, job_id: str) -> ProgramJob:
        """Return an adapter for the job.

        Args:
            job_id: ID of the job.

        Returns:
            The backend adapter.
        """
        return ProgramJob(self.session, job_id)

    # Client functions.

    def login(self, api_token: str) -> dict[str, Any]:
        """Login with token.

        Args:
            api_token: API token.

        Returns:
            JSON response.
        """
        url = self.get_url("login")
        return self.session.post(
            url, json={"apiToken": api_token}, headers=self._HEADER_JSON_CONTENT
        ).json()

    def user_info(self) -> dict[str, Any]:
        """Return user information.

        Returns:
            JSON response of user information.
        """
        url = self.get_url("user_info")

        response = self.session.get(url, headers=self._HEADER_JSON_ACCEPT).json()

        return response
