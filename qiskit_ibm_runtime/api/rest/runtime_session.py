# This code is part of Qiskit.
#
# (C) Copyright IBM 2022.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Runtime Session REST adapter."""

from typing import Dict, Any
from .base import RestAdapterBase
from ..session import RetrySession
from ..exceptions import RequestsApiError
from ...exceptions import IBMRuntimeError


class RuntimeSession(RestAdapterBase):
    """Rest adapter for session related endpoints."""

    URL_MAP = {
        "self": "",
        "close": "/close",
    }

    def __init__(self, session: RetrySession, session_id: str, url_prefix: str = "") -> None:
        """Job constructor.

        Args:
            session: RetrySession to be used in the adapter.
            session_id: Job ID of the first job in a runtime session.
            url_prefix: Prefix to use in the URL.
        """
        super().__init__(session, "{}/sessions/{}".format(url_prefix, session_id))

    def cancel(self) -> None:
        """Cancel all jobs in the session."""
        url = self.get_url("close")
        self.session.delete(url)

    def close(self) -> None:
        """Set accepting_jobs flag to false, so no more jobs can be submitted."""
        payload = {"accepting_jobs": False}
        url = self.get_url("self")
        try:
            self.session.patch(url, json=payload)
        except RequestsApiError as ex:
            if ex.status_code == 404:
                pass
            else:
                raise IBMRuntimeError(f"Error closing session: {ex}")

    def details(self) -> Dict[str, Any]:
        """Return the details of this session."""
        try:
            return self.session.get(self.get_url("self")).json()
        # return None if API is not supported
        except:  # pylint: disable=bare-except
            return None
