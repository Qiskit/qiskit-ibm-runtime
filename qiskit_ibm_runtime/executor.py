# This code is part of Qiskit.
#
# (C) Copyright IBM 2025.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Executor"""

from __future__ import annotations

from dataclasses import asdict
import logging

from ibm_quantum_schemas.models.base_params_model import BaseParamsModel

from qiskit_ibm_runtime.base_primitive import get_mode_service_backend
from qiskit_ibm_runtime.fake_provider.local_service import QiskitRuntimeLocalService
from .ibm_backend import IBMBackend
from .session import Session  # pylint: disable=cyclic-import
from .batch import Batch  # pylint: disable=cyclic-import
from .options.executor_options import ExecutorOptions
from .quantum_program import QuantumProgram
from .quantum_program.converters import quantum_program_to_0_1
from .quantum_program.quantum_program_decoders import QuantumProgramResultDecoder
from .runtime_job_v2 import RuntimeJobV2
from .runtime_options import RuntimeOptions
from .utils.default_session import get_cm_session

logger = logging.getLogger()


class Executor:
    """Executor for :class:`~.QuantumProgram`\\s."""

    _PROGRAM_ID = "executor"
    _DECODER = QuantumProgramResultDecoder

    def __init__(self, mode: IBMBackend | Session | Batch | None):
        self._options = ExecutorOptions()

        self._session, self._service, self._backend = get_mode_service_backend(mode)
        if isinstance(self._service, QiskitRuntimeLocalService):
            raise ValueError("The executor is currently not supported in local mode.")

    @property
    def options(self) -> ExecutorOptions:
        """The options of this executor."""
        return self._options

    def _runtime_options(self) -> RuntimeOptions:
        return RuntimeOptions(
            backend=self._backend.name,
            image=self.options.environment.image,
            job_tags=self.options.environment.job_tags,
            log_level=self.options.environment.log_level,
            private=self.options.environment.private,
            max_execution_time=self.options.environment.max_execution_time,
        )

    def _run(self, params: BaseParamsModel) -> RuntimeJobV2:
        runtime_options = self._runtime_options()

        if self._session:
            run = self._session._run
        else:
            run = self._service._run
            runtime_options.instance = self._backend._instance

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

        return run(
            program_id=self._PROGRAM_ID,
            options=asdict(runtime_options),
            inputs=inputs,
            result_decoder=self._DECODER,
            calibration_id=getattr(self._backend, "calibration_id", None),
        )

    def run(self, program: QuantumProgram) -> RuntimeJobV2:
        """Run a quantum program.

        Args:
            program: The program to run.

        Returns:
            A job.
        """
        return self._run(quantum_program_to_0_1(program, self.options))
