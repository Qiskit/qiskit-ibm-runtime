# This code is part of Qiskit.
#
# (C) Copyright IBM 2025-2026.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Executor program."""

from __future__ import annotations

import logging
from dataclasses import asdict
from typing import TYPE_CHECKING, Any

from qiskit_ibm_runtime.base_primitive import get_mode_service_backend
from qiskit_ibm_runtime.fake_provider.local_service import QiskitRuntimeLocalService

from ..options_models.executor_options import ExecutorOptions
from ..quantum_program.params_converters import QUANTUM_PROGRAM_PARAMS_CONVERTERS
from ..quantum_program.result_decoders import QuantumProgramResultDecoder
from ..utils.default_session import get_cm_session

if TYPE_CHECKING:
    from qiskit.providers import BackendV2

    from ..batch import Batch
    from ..quantum_program import QuantumProgram
    from ..runtime_job_v2 import RuntimeJobV2
    from ..session import Session


logger = logging.getLogger(__name__)


class Executor:
    r"""Class for running :class:`~.QuantumProgram`\\s.

    The :meth:`run` method can be used to submit a quantum program to be executed on a backend.

    .. code-block:: python

        from qiskit_ibm_runtime import QiskitRuntimeService, Executor, QuantumProgram

        service = QiskitRuntimeService()
        backend = service.backend("ibm_boston")

        program = QuantumProgram(shots=100)
        ... # add program contents

        executor = Executor(backend)
        executor.options.environment.job_tags = ["my_tag"]
        job = executor.run(program)

    Args:
        mode: The execution mode used to make the query. It can be:

            * A :class:`~.BackendV2` if you are using job mode.
            * A :class:`Session` if you are using session execution mode.
            * A :class:`Batch` if you are using batch execution mode.

            Refer to the
            `Qiskit Runtime documentation
            <https://quantum.cloud.ibm.com/docs/guides/execution-modes>`_
            for more information about the ``Execution modes``.

        options: Executor options, see :class:`ExecutorOptions` for detailed description.
            This can be an :class:`ExecutorOptions` instance or a dictionary that will be
            used to construct one.

    Raises:
        TypeError: If ``options`` is not a valid type.
        ValueError: If local mode is used.
    """

    _PROGRAM_ID = "executor"
    _DECODER = QuantumProgramResultDecoder
    _SCHEMA_VERSION = "v1.0"

    options: ExecutorOptions
    """The options of this executor."""

    def __init__(
        self,
        mode: BackendV2 | Session | Batch | None = None,
        options: ExecutorOptions | dict | None = None,
    ):
        # Coerced to `ExecutorOptions` via `__setattr__()`.
        self.options = options if options is not None else ExecutorOptions()  # type: ignore[assignment]

        self._session, self._service, self._backend = get_mode_service_backend(mode)
        if isinstance(self._service, QiskitRuntimeLocalService):
            raise ValueError("The executor is currently not supported in local mode.")

    def __setattr__(self, name: str, value: Any) -> None:
        """Set attribute ``name`` to ``value``.

        Handle ``options`` as a special case, ensuring it is set to an ``ExecutorOptions`` instance.
        This is an alternative to using ``@setter``, as the setter causes issues in ``ipython``
        autocomplete features.
        """
        if name == "options":
            if isinstance(value, dict):
                value = ExecutorOptions(**value)
            elif not isinstance(value, ExecutorOptions):
                raise TypeError(f"Expected ExecutorOptions or dict, got {type(value)}")

        super().__setattr__(name, value)

    def run(self, program: QuantumProgram) -> RuntimeJobV2:
        """Run a quantum program.

        Args:
            program: The program to run.

        Returns:
            A job.
        """
        try:
            converter = QUANTUM_PROGRAM_PARAMS_CONVERTERS[self._SCHEMA_VERSION]
        except KeyError:
            raise ValueError(f"No converters for schema version {self._SCHEMA_VERSION}.")

        params = converter.encoder(program, self.options)
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
                    "mode because the %s primitive was initialized outside the context manager. "
                    "Move the %s initialization inside the context manager to run in a "
                    "session/batch.",
                    self._PROGRAM_ID,
                    self._PROGRAM_ID,
                )

        inputs = params.model_dump(mode="json")

        return _run(
            program_id=self._PROGRAM_ID,
            options=runtime_options,
            inputs=inputs,
            result_decoder=self._DECODER,
            calibration_id=getattr(self._backend, "calibration_id", None),
        )

    def backend(self) -> BackendV2:
        """Return the backend the primitive query will be run on."""
        return self._backend
