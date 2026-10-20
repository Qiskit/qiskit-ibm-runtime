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

from ..base_primitive import get_mode_service_backend
from ..options_models.calibrator import CalibratorOptions
from ..options_models.converters import to_runtime_options
from ..utils.default_session import get_cm_session
from .params_converters import CALIBRATOR_PARAMS_CONVERTERS

if TYPE_CHECKING:
    from qiskit.providers import BackendV2

    from ..batch import Batch
    from ..runtime_job_v2 import RuntimeJobV2
    from ..session import Session


logger = logging.getLogger(__name__)


class Calibrator:
    r"""Class for calibrating a backend.

    A calibrator can be initialized only inside a session.
    The :meth:`run` method can be used to submit a calibration request for a backend.

    .. code-block:: python

        from qiskit_ibm_runtime import QiskitRuntimeService, Session, Calibrator

        service = QiskitRuntimeService()
        backend = service.backend("ibm_boston")

        with Session(backend=backend) as session:
            calibrator = Calibrator(session)
            calibrator.run()

    Args:
        mode: The execution mode used to make the primitive query. It can be:

            * A :class:`Backend` if you are using job mode.
            * A :class:`Session` if you are using session execution mode.
            * A :class:`Batch` if you are using batch execution mode.

            Refer to the
            `IBM Quantum Compute documentation
            <https://quantum.cloud.ibm.com/docs/guides/execution-modes>`_
            for more information about the ``Execution modes``.

        options: Calibrator options, see
            :class:`~qiskit_ibm_runtime.options_models.CalibratorOptions`
            for detailed description.
    """

    _PROGRAM_ID = "calibrate"
    _SCHEMA_VERSION = "v0.1"

    options: CalibratorOptions
    """The options of this calibrator."""

    def __init__(
        self,
        mode: BackendV2 | Session | Batch | str | None = None,
        options: CalibratorOptions | dict | None = None,
    ):
        # Coerced to `CalibratorOptions` via `__setattr__()`.
        self.options = options if options is not None else CalibratorOptions()  # type: ignore[assignment]

        self._mode, self._service, self._backend = get_mode_service_backend(mode)
        if self._service.is_local:
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

    def backend(self) -> BackendV2:
        """Return the backend to calibrate."""
        return self._backend

    @property
    def mode(self) -> Session | Batch | None:
        """Return the execution mode used by this primitive.

        Returns:
            Mode used by this primitive, or ``None`` if an execution mode is not used.
        """
        return self._mode

    def run(self) -> RuntimeJobV2:
        """Calibrate the backend.

        Returns:
            A calibration job.
        """
        inputs = {
            "options": self.options.model_dump(mode="json", exclude={"environment"}),
        }

        try:
            converter = CALIBRATOR_PARAMS_CONVERTERS[self._SCHEMA_VERSION]
        except KeyError:
            raise ValueError(f"No converters for schema version {self._SCHEMA_VERSION}.")

        params = converter.encoder(self.options)
        inputs = params.model_dump(mode="json")

        if self._mode:
            _run = self._mode._run
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
            inputs=inputs,
            calibration_id=getattr(self._backend, "calibration_id", None),
        )
