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

from concurrent.futures import wait
from datetime import datetime
from functools import reduce
from typing import TYPE_CHECKING, Any, Literal

from qiskit.primitives.primitive_job import PrimitiveJob

from ..decoders.defaults import DEFAULT_DECODERS
from ..exceptions import RuntimeJobTimeoutError
from ..utils.converters import local_to_utc

if TYPE_CHECKING:
    from collections.abc import Callable
    from concurrent.futures import Future

    from qiskit.primitives.containers import PrimitiveResult

    from ..models import BackendProperties
    from ..quantum_program.quantum_program import QuantumProgram
    from ..results.quantum_program import QuantumProgramResult
    from ..runtime_job_v2 import JobStatus
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

    JOB_FINAL_STATES: tuple[JobStatus, ...] = ("DONE", "CANCELLED", "ERROR")

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
        self._status: JobStatus | None = None
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
        # Same structure and value types as the metrics of a job run on the service: ISO 8601 UTC
        # timestamp strings, and no QPU usage charged for local jobs.
        return {
            "timestamps": {
                name: local_to_utc(value).isoformat().replace("+00:00", "Z")
                for name, value in (
                    ("created", self._created),
                    ("running", self._running),
                    ("finished", self._finished),
                )
            },
            "usage": {"qpu_charge_time_seconds": 0, "status": "complete"},
        }

    def status(self) -> JobStatus:
        """Return the status of the job.

        Returns:
            Status of this job, with the same values as the status of a job run on the service.
        """
        if self._status in self.JOB_FINAL_STATES:
            return self._status
        if self._future is None:
            return "INITIALIZING"
        if self._future.cancelled():
            self._status = "CANCELLED"
        elif self._future.done():
            self._status = "DONE" if self._future.exception() is None else "ERROR"
        else:
            # Only final states are stored, as the job can still move on from the others.
            return "RUNNING" if self._future.running() else "QUEUED"
        return self._status

    def cancelled(self) -> bool:
        """Return whether the job has been cancelled."""
        return self.status() == "CANCELLED"

    def done(self) -> bool:
        """Return whether the job has successfully run."""
        return self.status() == "DONE"

    def errored(self) -> bool:
        """Return whether the job has failed."""
        return self.status() == "ERROR"

    def in_final_state(self) -> bool:
        """Return whether the job is in a final job state such as ``DONE`` or ``ERROR``."""
        return self.status() in self.JOB_FINAL_STATES

    def running(self) -> bool:
        """Return whether the job is actively running."""
        return self.status() == "RUNNING"

    def wait_for_final_state(
        self,
        timeout: float | None = None,
        poll_interval: float | None = None,
    ) -> None:
        """Wait until the job is in a final state.

        Args:
            timeout: Seconds to wait for the job. If ``None``, wait indefinitely.
            poll_interval: Not used in local mode, where the job is waited on directly. Accepted
                for compatibility with jobs run on the service.

        Raises:
            RuntimeJobTimeoutError: If the job does not complete within given timeout.
        """
        self._check_submitted()
        if wait([self._future], timeout=timeout).not_done:
            raise RuntimeJobTimeoutError(
                f"Timed out waiting for job to complete after {timeout} secs."
            )

    def backend(self) -> FakeBackendV2:
        """Return the backend where this job was executed."""
        return self._backend

    def usage(self, partial: bool = False, resource_units: bool = False) -> float:
        """Return job usage in seconds.

        Args:
            partial: if ``True``, return the accumulated intermediate usage thus far until final
                usage is reached. Not used in local mode.
            resource_units: If ``True``, return usage in resource units instead of seconds. Not
                used in local mode.
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
            # Invoke all decoders, chaining them (one decoders output becomes the next's input) and
            # skipping the ones that are not applicable.
            return reduce(
                lambda result, decoder: decoder.decode(result)
                if decoder.is_applicable(result)
                else result,
                DEFAULT_DECODERS["executor"],
                result,
            )

        return result
