# This code is part of Qiskit.
#
# (C) Copyright IBM 2026.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Calibrator program."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from qiskit_ibm_runtime.base_primitive import get_mode_service_backend
from qiskit_ibm_runtime.fake_provider.local_service import QiskitRuntimeLocalService
from qiskit_ibm_runtime.decoders.result_decoder import ResultDecoder

from ..utils.default_session import get_cm_session

if TYPE_CHECKING:
    from qiskit.providers import BackendV2
    from ..runtime_job_v2 import RuntimeJobV2


logger = logging.getLogger(__name__)


class Calibrator:
    r"""Class for rcalibrating a backend.

    The :meth:`run` method can be used to submit a calibration request for a backend.

    .. code-block:: python

        from qiskit_ibm_runtime import QiskitRuntimeService, Calibrator

        service = QiskitRuntimeService()
        backend = service.backend("ibm_boston")

        calibrator = Calibrator(backend)
        job = calibrator.run()

    Args:
        backend: The backend to calibrate.
    """

    _PROGRAM_ID = "calibrator"
    _DECODER = ResultDecoder


    def __init__(
        self,
        backend: IBMBackendV2,
    ):
        self._session, self._service, self._backend = get_mode_service_backend(backend)
        if isinstance(self._service, QiskitRuntimeLocalService):
            raise ValueError("The calibrator is currently not supported in local mode.")

    def run(self) -> RuntimeJobV2:
        """Calibrate the backend.

        Returns:
            A calibration job.
        """
        if self._session:
            _run = self._session._run
        else:
            _run = self._service._run

            if get_cm_session():
                logger.warning(
                    "Even though a session/batch context manager is open this job will run in job "
                    "mode because the %s program was initialized outside the context manager. "
                    "Move the %s initialization inside the context manager to run in a "
                    "session/batch.",
                    self._PROGRAM_ID,
                    self._PROGRAM_ID,
                )

        return _run(
            program_id=self._PROGRAM_ID,
            options={"backend": backend},
            inputs={},
            result_decoder=self._DECODER,
        )

    def backend(self) -> BackendV2:
        """Return the backend to calibrate."""
        return self._backend