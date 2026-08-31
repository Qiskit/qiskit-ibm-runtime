# This code is part of Qiskit.
#
# (C) Copyright IBM 2024-2026.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Qiskit runtime local mode job class."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, Literal

from qiskit.primitives.primitive_job import PrimitiveJob

from ..decoders.quantum_program.decoder import QuantumProgramResultDecoder

if TYPE_CHECKING:
    from collections.abc import Callable
    from concurrent.futures import Future

    from qiskit.primitives.containers import PrimitiveResult

    from ..models import BackendProperties
    from ..quantum_program.quantum_program import QuantumProgram
    from ..results.quantum_program import QuantumProgramResult
    from .fake_backend import FakeBackendV2


class LocalRuntimeJob(PrimitiveJob):
    """Job class for qiskit-ibm-runtime's local mode.

    This job supports both V2 primitives, and the Executor primitive. For the Executor primitive,
    the results are post-processed, and the ``function`` is expected to have the signature:
    ```
    (
    backend: BackendV2,
    program: QuantumProgram,
    options: SimulatorOptions,
    ) -> QuantumProgramResult:
    ```

    Args:
        function: The callable that is invoked when the job is submitted.
        future: Thread executor the job is run on. If not specified, a new ``future`` is created
            when the job is submitted.
        backend: The backend to run the primitive on.
        primitive: Name of the primitive.
        inputs: Program input parameters.
        args: Additional arguments to pass to the ``function``.
        kwargs: Additional keyword arguments to pass to the ``function``.
    """

    def __init__(  # type: ignore[no-untyped-def]
        self,
        function: Callable,
        backend: FakeBackendV2,
        primitive: Literal["sampler", "estimator", "executor"],
        inputs: dict | QuantumProgram,
        future: Future | None = None,
        *args,
        **kwargs,
    ) -> None:
        if primitive == "executor":
            # Pass extra arguments for the function used for executor jobs.
            kwargs.update({"backend": backend, "program": inputs})
        super().__init__(function, *args, **kwargs)

        self._future = future
        self._backend = backend
        self._primitive = primitive
        self._inputs = inputs
        self._created = datetime.now()
        self._running = datetime.now()
        self._finished = datetime.now()

    def metrics(self) -> dict[str, Any]:
        """Return job metrics.

        Returns:
            A dictionary with job metrics including but not limited to the following:

            * ``timestamps``: Timestamps of when the job was created, started running, and finished.
            * ``usage``: Details regarding job usage, the measurement of the amount of
                time the QPU is locked for your workload.
        """
        return {
            "bss": {"seconds": 0},
            "usage": {"quantum_seconds": 0, "seconds": 0},
            "timestamps": {
                "created": self._created,
                "running": self._running,
                "finished": self._finished,
            },
        }

    def backend(self) -> FakeBackendV2:
        """Return the backend where this job was executed."""
        return self._backend

    def usage(self, partial: bool = False) -> float:
        """Return job usage in seconds.

        Args:
            partial: if ``True``, return the accumulated intermediate usage thus far until final
                usage is reached.
        """
        return 0

    def properties(self) -> BackendProperties:
        """Return the backend properties for this job."""
        return self._backend.properties()

    def error_message(self) -> str:
        """Returns the reason if the job failed."""
        return ""

    @property
    def inputs(self) -> dict | QuantumProgram:
        """Return job input parameters."""
        return self._inputs

    @property
    def session_id(self) -> str:
        """Return the Session ID which would just be the job ID in local mode."""
        return self._job_id

    @property
    def creation_date(self) -> datetime:
        """Job creation date in local time."""
        return self._created

    @property
    def primitive_id(self) -> str:
        """Primitive name."""
        return self._primitive

    def result(self) -> PrimitiveResult | QuantumProgramResult:
        """Return the results of the job."""
        result = super().result()

        if self.primitive_id == "executor":
            return QuantumProgramResultDecoder._apply_post_processing(result)

        return result
