# This code is part of Qiskit.
#
# (C) Copyright IBM 2023.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Qiskit Runtime batch mode."""

from typing import Optional, Union
from qiskit_ibm_runtime import QiskitRuntimeService
from .ibm_backend import IBMBackend

from .session import Session


class Batch(Session):
    """Class for creating a batch mode in Qiskit Runtime."""

    def __init__(
        self,
        service: Optional[QiskitRuntimeService] = None,
        backend: Optional[Union[str, IBMBackend]] = None,
        max_time: Optional[Union[int, str]] = None,
    ):
        super().__init__(service=service, backend=backend, max_time=max_time)

    def _create_session(self) -> str:
        """Create a session."""
        session = self._service._api_client.create_session(
            self._backend, self._instance, self._max_time, self._service.channel, "batch"
        )
        return session.get("id")
