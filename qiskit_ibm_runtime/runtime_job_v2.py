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

"""Qiskit runtime job."""

from __future__ import annotations

from typing import Any, Literal
from collections.abc import Sequence
from concurrent import futures
from functools import reduce
import logging
import time
import warnings

from qiskit.providers.backend import Backend
from qiskit.primitives.containers import PrimitiveResult
from qiskit.primitives.base.base_primitive_job import BasePrimitiveJob

from qiskit_ibm_runtime import qiskit_runtime_service
from .exceptions import (
    RuntimeJobFailureError,
    RuntimeInvalidStateError,
    IBMRuntimeError,
    RuntimeJobMaxTimeoutError,
    RuntimeJobTimeoutError,
)
from .decoders.result_decoder import ResultDecoder
from .api.clients import RuntimeClient
from .api.exceptions import RequestsApiError
from .base_runtime_job import BaseRuntimeJob

logger = logging.getLogger(__name__)

JobStatus = Literal["INITIALIZING", "QUEUED", "RUNNING", "CANCELLED", "DONE", "ERROR"]
API_TO_JOB_STATUS: dict[str, JobStatus] = {
    "QUEUED": "QUEUED",
    "RUNNING": "RUNNING",
    "COMPLETED": "DONE",
    "FAILED": "ERROR",
    "CANCELLED": "CANCELLED",
}


class RuntimeJobV2(BasePrimitiveJob[PrimitiveResult, JobStatus], BaseRuntimeJob):
    """Representation of a runtime V2 primitive execution.

    Args:
        backend: The backend instance used to run this job.
        api_client: Object for connecting to the server.
        job_id: Job ID.
        program_id: ID of the program this job is for.
        creation_date: Job creation date, in UTC.
        result_decoder: A :class:`ResultDecoder` subclass used to decode job results, or a list
            of such subclasses. If more than one decoder is specified, they will be called in
            chain, with the output of the ``n-th`` decoder as the input of the ``n+1-th``
            decoder. If not specified, the default ``ResultDecoder`` is used.
        image: Runtime image used for this job: image_name:tag.
        service: Runtime service.
        session_id: Job ID of the first job in a runtime session.
        tags: Tags assigned to the job.
        version: Primitive version.
        private: Marks job as private.
    """

    JOB_FINAL_STATES: tuple[JobStatus, ...] = ("DONE", "CANCELLED", "ERROR")
    ERROR = "ERROR"

    def __init__(
        self,
        backend: Backend,
        api_client: RuntimeClient,
        job_id: str,
        program_id: str,
        service: qiskit_runtime_service.QiskitRuntimeService,
        creation_date: str | None = None,
        result_decoder: type[ResultDecoder] | Sequence[type[ResultDecoder]] | None = None,
        image: str | None = "",
        session_id: str | None = None,
        tags: list | None = None,
        version: int | None = None,
        private: bool | None = False,
    ) -> None:
        BasePrimitiveJob.__init__(self, job_id=job_id)
        BaseRuntimeJob.__init__(
            self,
            backend=backend,
            api_client=api_client,
            job_id=job_id,
            program_id=program_id,
            service=service,
            creation_date=creation_date,
            result_decoder=result_decoder,
            image=image,
            session_id=session_id,
            tags=tags,
            version=version,
            private=private,
        )
        self._status: JobStatus = "INITIALIZING"

    def result(
        self,
        timeout: float | None = None,
        decoder: type[ResultDecoder] | Sequence[type[ResultDecoder]] | None = None,
        poll_interval: float | None = None,
    ) -> Any:
        """Return the results of the job.

        Args:
            timeout: Number of seconds to wait for job.
            decoder: A :class:`ResultDecoder` subclass used to decode job results.
            poll_interval: Number of seconds to wait between successive queries of the job's status.
                of the job.

                * For non-session jobs, the default is ``500ms``, and the floor value is ``100ms``.
                * For session jobs, the default and the floor value are ``100ms``.

        Returns:
            Runtime job result (post-processed if applicable).

        Raises:
            RuntimeJobFailureError: If the job failed.
            RuntimeJobMaxTimeoutError: If the job does not complete within given timeout.
            RuntimeInvalidStateError: If the job was cancelled, and attempting to retrieve result.
        """
        if decoder and not isinstance(decoder, Sequence):
            decoder = [decoder]
        decoders = decoder or self._result_decoders

        self.wait_for_final_state(timeout=timeout, poll_interval=poll_interval)
        if self._status == "ERROR":
            error_message = self._reason if self._reason else self._error_message
            if self._reason_code == 1305:
                raise RuntimeJobMaxTimeoutError(error_message)
            raise RuntimeJobFailureError(f"Unable to retrieve job result. {error_message}")
        if self._status == "CANCELLED":
            raise RuntimeInvalidStateError(
                f"Unable to retrieve result for job {self.job_id()}. Job was cancelled."
            )

        result_raw = self._api_client.job_results(job_id=self.job_id())
        # Invoke all decoders, chaining them (one decoders output becomes the next's input).
        return reduce(lambda x, d: d.decode(x), decoders, result_raw) if result_raw else None

    def cancel(self) -> None:
        """Cancel the job.

        Raises:
            RuntimeInvalidStateError: If the job is in a state that cannot be cancelled.
            IBMRuntimeError: If unable to cancel job.
        """
        try:
            self._api_client.job_cancel(self.job_id())
        except RequestsApiError as ex:
            if ex.status_code == 409:
                raise RuntimeInvalidStateError(f"Job cannot be cancelled: {ex}") from None
            raise IBMRuntimeError(f"Failed to cancel job: {ex}") from None
        self._status = "CANCELLED"

    def status(self) -> JobStatus:
        """Return the status of the job.

        Returns:
            Status of this job.
        """
        self._set_status_and_error_message()
        return self._status

    def _status_from_job_response(self, response: dict) -> JobStatus | str:
        """Returns the job status from an API response.

        Args:
            response: Job response from the runtime API.

        Returns:
            Job status.
        """
        api_status = response["state"]["status"].upper()
        if api_status in API_TO_JOB_STATUS:
            mapped_job_status = API_TO_JOB_STATUS[api_status]
            if mapped_job_status == "CANCELLED" and self._reason_code == 1305:
                mapped_job_status = "ERROR"
            return mapped_job_status
        return api_status

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

    def logs(self) -> str:
        """Return job logs.

        Note:
            Job logs are only available after the job finishes.

        Returns:
            Job logs, including standard output and error.

        Raises:
            IBMRuntimeError: If a network error occurred.
        """
        if self.status() not in self.JOB_FINAL_STATES:
            logger.warning("Job logs are only available after the job finishes.")
        try:
            return self._api_client.job_logs(self.job_id())
        except RequestsApiError as err:
            if err.status_code == 404:
                return ""
            raise IBMRuntimeError(f"Failed to get job logs: {err}") from None

    def wait_for_final_state(
        self,
        timeout: float | None = None,
        poll_interval: float | None = None,
    ) -> None:
        """Poll for the job status from the API until the status is in a final state.

        Args:
            timeout: Seconds to wait for the job. If ``None``, wait indefinitely.
            poll_interval: Number of seconds to wait between querying the service for the status
                of the job.

                * For non-session jobs, the default is ``500ms``, and the floor value is ``100ms``.
                * For session jobs, the default and the floor value is ``100ms``.

        Raises:
            RuntimeJobTimeoutError: If the job does not complete within given timeout.
        """
        # Calculate the poll interval.
        min_poll_interval = 0.1
        default_poll_interval = 0.1 if self._session_id else 0.5
        if poll_interval and poll_interval < 0.1:
            warnings.warn(
                "The poll interval specified is lower than the minimal allowed. Using "
                f"{min_poll_interval} as the poll interval."
            )
        poll_interval = max(min_poll_interval, poll_interval or default_poll_interval)

        try:
            start_time = time.time()
            status = self.status()
            while status not in self.JOB_FINAL_STATES:
                elapsed_time = time.time() - start_time
                if timeout is not None and elapsed_time >= timeout:
                    raise RuntimeJobTimeoutError(
                        f"Timed out waiting for job to complete after {timeout} secs."
                    )
                time.sleep(poll_interval)
                status = self.status()
        except futures.TimeoutError:
            raise RuntimeJobTimeoutError(
                f"Timed out waiting for job to complete after {timeout} secs."
            )

    def backend(self, timeout: float | None = None) -> Backend | None:
        """Return the backend where this job was executed. Retrieve data again if backend is None.

        Raises:
            IBMRuntimeError: If a network error occurred.
        """
        if not self._backend:
            self.wait_for_final_state(timeout=timeout)
            try:
                raw_data = self._api_client.job_get(self.job_id())
                if raw_data.get("backend"):
                    self._backend = self._service.backend(raw_data["backend"])
            except RequestsApiError as err:
                raise IBMRuntimeError(f"Failed to get job backend: {err}") from None
        return self._backend
