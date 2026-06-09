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
from dataclasses import asdict
from typing import TYPE_CHECKING

from qiskit_ibm_runtime.base_primitive import get_mode_service_backend
from qiskit_ibm_runtime.decoders.result_decoder import ResultDecoder
from qiskit_ibm_runtime.fake_provider.local_service import QiskitRuntimeLocalService
from qiskit_ibm_runtime.options_models.calibrator_options import CalibratorOptions
from qiskit_ibm_runtime.utils.default_session import get_cm_session

if TYPE_CHECKING:
    from qiskit.providers import BackendV2

    from ..runtime_job_v2 import RuntimeJobV2
    from .batch import Batch
    from .session import Session


logger = logging.getLogger(__name__)


class Calibrator:
    r"""Class for calibrating a backend.

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

    _PROGRAM_ID = "calibrate"
    _DECODER = ResultDecoder

    options: CalibratorOptions
    """The options of this calibrator."""

    def __init__(
        self,
        mode: BackendV2 | Session | Batch | str | None = None,
        options: CalibratorOptions | dict | None = None,
    ):
        if options is None:
            self.options = CalibratorOptions()
        elif isinstance(options, dict):
            self.options = CalibratorOptions(**options)
        else:
            self.options = options

        self._session, self._service, self._backend = get_mode_service_backend(mode)
        if isinstance(self._service, QiskitRuntimeLocalService):
            raise ValueError("The calibrator is currently not supported in local mode.")

    def run(self) -> RuntimeJobV2:
        """Calibrate the backend.

        Returns:
            A calibration job.
        """
        runtime_options = asdict(self.options.environment)  # type: ignore[call-overload]
        runtime_options["backend"] = self._backend.name
        runtime_options["instance"] = self._backend._instance

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
            options=runtime_options,
            #inputs={},
            inputs={"options": {"experimental": {"skip_jps_validation": True}}},
            result_decoder=self._DECODER,
        )

    def backend(self) -> BackendV2:
        """Return the backend to calibrate."""
        return self._backend
