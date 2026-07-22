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
from typing import TYPE_CHECKING, Any

from .base_primitive import get_mode_service_backend
from .fake_provider.local_service import QiskitRuntimeLocalService
from .options_models.calibrator import CalibratorOptions
from .options_models.converters import to_runtime_options
from .utils.default_session import get_cm_session

if TYPE_CHECKING:
    from qiskit.providers import BackendV2

    from .batch import Batch
    from .runtime_job_v2 import RuntimeJobV2
    from .session import Session


logger = logging.getLogger(__name__)


class Calibrator:
    r"""Class for calibrating a backend.

    The :meth:`run` method can be used to submit a calibration request for a backend.

    .. code-block:: python

        from qiskit_ibm_runtime import QiskitRuntimeService
        from qiskit_ibm_runtime.calibrator import Calibrator

        service = QiskitRuntimeService()
        backend = service.backend("ibm_boston")

        calibrator = Calibrator(backend)
        job = calibrator.run()

    Args:
        backend: The backend to calibrate.
    """

    _PROGRAM_ID = "calibrate"

    options: CalibratorOptions
    """The options of this calibrator."""

    def __init__(
        self,
        mode: BackendV2 | Session | Batch | str | None = None,
        options: CalibratorOptions | dict | None = None,
    ):
        # Coerced to `CalibratorOptions` via `__setattr__()`.Expand comment
        self.options = options if options is not None else CalibratorOptions()  # type: ignore[assignment]

        self._session, self._service, self._backend = get_mode_service_backend(mode)
        if isinstance(self._service, QiskitRuntimeLocalService):
            raise ValueError("The calibrator is currently not supported in local mode.")

    def __setattr__(self, name: str, value: Any) -> None:
        """Set attribute ``name`` to ``value``.

        Handle ``options`` as a special case, ensuring it is set to a ``CalibratorOptions``
        instance. This is an alternative to using ``@setter``, as the setter causes issues in
        ``ipython`` autocomplete features.
        """
        if name == "options":
            if isinstance(value, dict):
                value = CalibratorOptions(**value)
            elif not isinstance(value, CalibratorOptions):
                raise TypeError(f"Expected CalibratorOptions or dict, got {type(value)}")

        super().__setattr__(name, value)

    def run(self) -> RuntimeJobV2:
        """Calibrate the backend.

        Returns:
            A calibration job.
        """
        options_dict = {}
        if self.options.experimental:
            options_dict["experimental"] = self.options.experimental

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
            options=to_runtime_options(self.options.environment, self._backend),
            inputs={"options": options_dict},
            calibration_id=getattr(self._backend, "calibration_id", None),
        )

    def backend(self) -> BackendV2:
        """Return the backend to calibrate."""
        return self._backend
