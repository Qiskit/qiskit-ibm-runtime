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

"""IBM Quantum Compute job."""

from __future__ import annotations

import logging
import time
import warnings
from collections.abc import Sequence
from functools import reduce
from typing import TYPE_CHECKING, Any, Literal

from qiskit.primitives.base.base_primitive_job import BasePrimitiveJob
from qiskit.primitives.containers import PrimitiveResult

from .api.exceptions import RequestsApiError
from .decoders.defaults import DEFAULT_DECODERS
from .decoders.result_decoder import ResultDecoder
from .exceptions import (
    IBMApiError,
    IBMError,
    IBMRuntimeError,
    RuntimeInvalidStateError,
    RuntimeJobFailureError,
    RuntimeJobMaxTimeoutError,
    RuntimeJobTimeoutError,
)
from .utils import utc_to_local, validate_job_tags

if TYPE_CHECKING:
    from datetime import datetime

    from qiskit.providers.backend import Backend
    from qiskit.providers.jobstatus import JobStatus as RuntimeJobStatus

    from .api.client import RuntimeClient
    from .models import BackendProperties
    from .qiskit_runtime_service import QiskitRuntimeService

logger = logging.getLogger(__name__)

JobStatus = Literal["INITIALIZING", "QUEUED", "RUNNING", "CANCELLED", "DONE", "ERROR"]

API_TO_JOB_ERROR_MESSAGE = {
    "FAILED": "Job {} has failed:\n{}",
    "CANCELLED - RAN TOO LONG": "Job {} ran longer than maximum execution time. "
    "Job was cancelled:\n{}",
}

API_TO_JOB_STATUS: dict[str, JobStatus] = {
    "QUEUED": "QUEUED",
    "RUNNING": "RUNNING",
    "COMPLETED": "DONE",
    "FAILED": "ERROR",
    "CANCELLED": "CANCELLED",
}


class RuntimeJobV2(BasePrimitiveJob[PrimitiveResult, JobStatus]):
    """Representation of a IBM Quantum Compute (formerly Qiskit Runtime) V2 primitive execution.

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
        image: IBM Quantum Compute image used for this job: image_name:tag.
        service: IBM Quantum Compute service.
        session_id: Job ID of the first job in a IBM Quantum Compute session.
        tags: Tags assigned to the job.
        version: Primitive version.
        private: Marks job as private.
    """

    JOB_FINAL_STATES: tuple[JobStatus, ...] = ("DONE", "CANCELLED", "ERROR")
    ERROR: str | RuntimeJobStatus = "ERROR"

    def __init__(
        self,
        backend: Backend,
        api_client: RuntimeClient,
        job_id: str,
        program_id: str,
        service: QiskitRuntimeService,
        creation_date: str | None = None,
        result_decoder: type[ResultDecoder] | Sequence[type[ResultDecoder]] | None = None,
        image: str | None = "",
        session_id: str | None = None,
        tags: list | None = None,
        version: int | None = None,
        private: bool | None = False,
    ) -> None:
        BasePrimitiveJob.__init__(self, job_id=job_id)
        self._backend = backend
        self._job_id = job_id
        self._api_client = api_client
        self._creation_date = creation_date
        self._program_id = program_id
        self._reason: str | None = None
        self._reason_code: int | None = None
        self._error_message: str | None = None
        self._image = image
        self._service = service
        self._session_id = session_id
        self._tags = tags
        self._usage_estimation: dict[str, Any] = {}
        self._version = version
        self._queue_info = None
        self._private = private
        self._status: JobStatus = "INITIALIZING"

        # Store the list of decoders for this job.
        decoder = result_decoder or DEFAULT_DECODERS.get(program_id, None) or ResultDecoder
        if not isinstance(decoder, Sequence):
            self._result_decoders: Sequence[type[ResultDecoder]] = [decoder]
        else:
            self._result_decoders = decoder

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}('{self._job_id}', '{self._program_id}')>"

    def job_id(self) -> str:
        """Return a unique id identifying the job."""
        return self._job_id

    @property
    def private(self) -> bool:
        """Returns a boolean indicating whether or not the job is private."""
        return self._private

    @property
    def image(self) -> str:
        """Return the IBM Quantum Compute image used for the job.

        Returns:
            The IBM Quantum Compute image ``image_name:tag`` or ``""`` if the default image is used.
        """
        return self._image

    @property
    def inputs(self) -> dict:
        """Job input parameters.

        Returns:
            Input parameters used in this job.
        """
        response = self._api_client.job_get(job_id=self.job_id(), exclude_params=False)
        return response.get("params", {})

    @property
    def primitive_id(self) -> str:
        """Primitive name.

        Returns:
            Primitive this job is for.
        """
        return self._program_id

    @property
    def creation_date(self) -> datetime | None:
        """Job creation date in local time.

        Returns:
            The job creation date as a datetime object, in local time, or
            ``None`` if creation date is not available.
        """
        if not self._creation_date:
            response = self._api_client.job_get(job_id=self.job_id())
            self._creation_date = response.get("created", None)

        if not self._creation_date:
            return None
        creation_date_local_dt = utc_to_local(self._creation_date)
        return creation_date_local_dt

    @property
    def session_id(self) -> str:
        """Session ID.

        Returns:
            Session ID. None if the backend is a simulator.
        """
        if not self._session_id:
            response = self._api_client.job_get(job_id=self.job_id())
            self._session_id = response.get("session_id", None)
        return self._session_id

    @property
    def tags(self) -> list:
        """Job tags.

        Returns:
            Tags assigned to the job that can be used for filtering.
        """
        return self._tags

    @property
    def usage_estimation(self) -> dict[str, Any]:
        """Return the usage estimation information for this job.

        Returns:
            ``quantum_seconds`` which is the estimated system execution time
            of the job in seconds. Quantum time represents the time that
            the system is dedicated to processing your job.
        """
        if not self._usage_estimation:
            response = self._api_client.job_get(job_id=self.job_id())
            self._usage_estimation = {
                "quantum_seconds": response.pop("estimated_running_time_seconds", None),
            }

        return self._usage_estimation

    @property
    def instance(self) -> str | None:
        """Return the IBM Cloud instance CRN."""
        return self._backend._instance

    def status(self) -> JobStatus:
        """Return the status of the job.

        Returns:
            Status of this job.
        """
        self._set_status_and_error_message()
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

    def error_message(self) -> str | None:
        """Returns the reason if the job failed.

        Returns:
            Error message string or ``None``.
        """
        self._set_status_and_error_message()
        if self._status == self.ERROR and self._error_message is None:
            response = self._api_client.job_get(job_id=self.job_id())
            self._set_error_message(response)
        return self._error_message

    def result(
        self,
        timeout: float | None = None,
        decoder: type[ResultDecoder] | Sequence[type[ResultDecoder]] | None = None,
        poll_interval: float | None = None,
    ) -> Any:
        """Return the results of the job.

        Args:
            timeout: Number of seconds to wait for job.
            decoder: A :class:`ResultDecoder` subclass used to decode job results, or a list
                of such subclasses. If more than one decoder is specified, they will be called in
                chain, with the output of the ``n-th`` decoder as the input of the ``n+1-th``
                decoder.
            poll_interval: Number of seconds to wait between successive queries of the job's status.
                of the job.

                * For non-session jobs, the default is ``500ms``, and the floor value is ``100ms``.
                * For session jobs, the default and the floor value are ``100ms``.

        Returns:
            IBM Quantum Compute job result (post-processed if applicable).

        Raises:
            RuntimeJobFailureError: If the job failed.
            RuntimeJobMaxTimeoutError: If the job does not complete within given timeout.
            RuntimeInvalidStateError: If the job was cancelled, and attempting to retrieve result.
        """
        if decoder and not isinstance(decoder, Sequence):
            decoder = [decoder]
        decoders: Sequence[type[ResultDecoder]] = decoder or self._result_decoders  # type: ignore[assignment]

        self.wait_for_final_state(timeout=timeout, poll_interval=poll_interval)
        if self._status == "ERROR":
            error_message = self._reason if self._reason else self.error_message()
            if self._reason_code == 1305:
                raise RuntimeJobMaxTimeoutError(error_message)
            raise RuntimeJobFailureError(f"Unable to retrieve job result. {error_message}")
        if self._status == "CANCELLED":
            raise RuntimeInvalidStateError(
                f"Unable to retrieve result for job {self.job_id()}. Job was cancelled."
            )

        result_raw = self._api_client.job_results(job_id=self.job_id())
        # Invoke all decoders, chaining them (one decoders output becomes the next's input) and
        # skipping the ones that are not applicable.
        return (
            reduce(
                lambda result, decoder: decoder.decode(result)
                if decoder.is_applicable(result)
                else result,
                decoders,
                result_raw,
            )
            if result_raw
            else None
        )

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

    def usage(self, partial: bool = False) -> float:
        """Return job usage in seconds.

        By default, the job usage returned is ``0`` until the usage calculation is
        completed. Accumulated intermediate usage can be returned by the method by using the
        ``partial`` flag.

        .. note::
            When using ``partial``, note that is not guaranteed that the final usage is returned as
            soon as the job is completed. It is recommended to invoke the method with
            ``partial=False`` for guarantees that the usage returned is final, or to use the
            :meth:`.metrics` method for details on the completion status.

        Args:
            partial: if ``True``, return the accumulated intermediate usage thus far until final
                usage is reached.
        """
        try:
            metrics = self._api_client.job_metadata(self.job_id())
            usage = metrics.get("usage", {})
            if partial:
                return usage.get("qpu_charge_time_seconds")
            if usage.get("status", "pending") == "pending":
                return 0
            return usage.get("qpu_charge_time_seconds")
        except RequestsApiError as err:
            raise IBMRuntimeError(f"Failed to get job metadata: {err}") from None

    def metrics(self) -> dict[str, Any]:
        """Return job metrics.

        Returns:
            A dictionary with job metrics including but not limited to the following:

            * ``timestamps``: Timestamps of when the job was created, started running, and finished.
            * ``usage``: Details regarding job usage, the measurement of the amount of
                time the QPU is locked for your workload.

        Raises:
            IBMRuntimeError: If a network error occurred.
        """
        try:
            return self._api_client.job_metadata(self.job_id())
        except RequestsApiError as err:
            raise IBMRuntimeError(f"Failed to get job metadata: {err}") from None

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

    def properties(self, refresh: bool = False) -> BackendProperties | None:
        """Return the backend properties for this job.

        Args:
            refresh: If ``True``, re-query the server for the backend properties.
                Otherwise, return a cached version.

        Returns:
            The backend properties used for this job, at the time the job started running,
            or ``None`` if properties are not available.
        """
        job_date = self.creation_date
        job_running_date = self.metrics().get("timestamps", {}).get("running")
        if job_running_date:
            job_date = utc_to_local(job_running_date)
        return self._backend.properties(refresh, job_date)

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

    def update_tags(self, new_tags: list[str]) -> list[str]:
        """Update the tags associated with this job.

        Args:
            new_tags: New tags to assign to the job.

        Returns:
            The new tags associated with this job.

        Raises:
            IBMApiError: If an unexpected error occurred when communicating
                with the server or updating the job tags.
        """
        tags_to_update = set(new_tags)
        validate_job_tags(new_tags)

        response = self._api_client.update_tags(job_id=self.job_id(), tags=list(tags_to_update))

        if response.status_code == 204:
            api_response = self._api_client.job_get(self.job_id())
            self._tags = api_response.pop("tags", [])
            return self._tags
        else:
            raise IBMApiError(
                "An unexpected error occurred when updating the "
                f"tags for job {self.job_id()}. The tags were not updated for "
                "the job."
            )

    def _set_status_and_error_message(self) -> None:
        """Fetch and set status and error message."""
        if self._status not in self.JOB_FINAL_STATES:
            response = self._api_client.job_get(job_id=self.job_id())
            self._set_status(response)
            self._set_error_message(response)

    def _set_status(self, job_response: dict) -> None:
        """Set status.

        Args:
            job_response: Job response from IBM Quantum Compute API.

        Raises:
            IBMError: If an unknown status is returned from the server.
        """
        try:
            reason = job_response["state"].get("reason")
            reason_code = job_response["state"].get("reasonCode") or job_response["state"].get(
                "reason_code"
            )
            if reason:
                self._reason = reason
                if reason_code:
                    self._reason = f"Error code {reason_code}; {self._reason}"
                    self._reason_code = reason_code
            self._status = self._status_from_job_response(job_response)
        except KeyError:
            raise IBMError(f"Unknown status: {job_response['state']['status']}")

    def _status_from_job_response(self, response: dict) -> JobStatus:
        """Returns the job status from an API response.

        Args:
            response: Job response from the IBM Quantum Compute API.

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

    def _set_error_message(self, job_response: dict) -> None:
        """Set error message if the job failed.

        Args:
            job_response: Job response from IBM Quantum Compute API.
        """
        if self._status == self.ERROR:
            self._error_message = self._error_msg_from_job_response(job_response)
        else:
            self._error_message = None

    def _error_msg_from_job_response(self, response: dict) -> str:
        """Returns the error message from an API response.

        Args:
            response: Job response from the IBM Quantum Compute API.

        Returns:
            Error message.
        """
        status = response["state"]["status"].upper()

        job_result_raw = self._api_client.job_results(job_id=self.job_id())

        index = job_result_raw.rfind("Traceback")
        if index != -1:
            job_result_raw = job_result_raw[index:]

        if status == "CANCELLED" and self._reason_code == 1305:
            error_msg = API_TO_JOB_ERROR_MESSAGE["CANCELLED - RAN TOO LONG"]
            return error_msg.format(self.job_id(), job_result_raw)
        else:
            error_msg = API_TO_JOB_ERROR_MESSAGE["FAILED"]
            return error_msg.format(self.job_id(), self._reason or job_result_raw)
