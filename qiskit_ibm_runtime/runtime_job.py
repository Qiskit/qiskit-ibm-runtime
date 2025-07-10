# This code is part of Qiskit.
#
# (C) Copyright IBM 2022.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Qiskit runtime job."""

from typing import Any, Optional, Callable, Dict, Type, Union, Sequence, List
from concurrent import futures
import logging
import time
import warnings

from qiskit.providers.backend import Backend
from qiskit.providers.jobstatus import JobStatus, JOB_FINAL_STATES
from qiskit.providers.job import JobV1 as Job

# pylint: disable=unused-import,cyclic-import

from qiskit_ibm_runtime import qiskit_runtime_service
from .constants import API_TO_JOB_STATUS
from .exceptions import (
    RuntimeJobFailureError,
    RuntimeInvalidStateError,
    IBMRuntimeError,
    RuntimeJobMaxTimeoutError,
    RuntimeJobTimeoutError,
)
from .utils.result_decoder import ResultDecoder
from .utils.deprecation import issue_deprecation_msg
from .api.clients import RuntimeClient
from .api.exceptions import RequestsApiError
from .api.client_parameters import ClientParameters
from .base_runtime_job import BaseRuntimeJob

logger = logging.getLogger(__name__)


class RuntimeJob(Job, BaseRuntimeJob):
    """Representation of a runtime primitive execution.

    A new ``RuntimeJob`` instance is returned when you call
    :meth:`QiskitRuntimeService.run<qiskit_ibm_runtime.QiskitRuntimeService.run>`
    to execute a runtime primitive, or
    :meth:`QiskitRuntimeService.job<qiskit_ibm_runtime.QiskitRuntimeService.job>`
    to retrieve a previously executed job.

    If the primitive execution is successful, you can inspect the job's status by
    calling :meth:`status()`. Job status can be one of the
    :class:`~qiskit.providers.JobStatus` members.

    Some of the methods in this class are blocking, which means control may
    not be returned immediately. :meth:`result()` is an example
    of a blocking method::

        job = service.run(...)

        try:
            job_result = job.result()  # It will block until the job finishes.
            print("The job finished with result {}".format(job_result))
        except RuntimeJobFailureError as ex:
            print("Job failed!: {}".format(ex))
    """

    JOB_FINAL_STATES = JOB_FINAL_STATES
    ERROR = JobStatus.ERROR

    def __init__(
        self,
        backend: Backend,
        api_client: RuntimeClient,
        job_id: str,
        program_id: str,
        service: "qiskit_runtime_service.QiskitRuntimeService",
        client_params: Optional[ClientParameters] = None,
        creation_date: Optional[str] = None,
        user_callback: Optional[Callable] = None,
        result_decoder: Optional[Union[Type[ResultDecoder], Sequence[Type[ResultDecoder]]]] = None,
        image: Optional[str] = "",
        session_id: Optional[str] = None,
        tags: Optional[List] = None,
        version: Optional[int] = None,
    ) -> None:
        """(DEPRECATED) RuntimeJob constructor.

        Args:
            backend: The backend instance used to run this job.
            api_client: Object for connecting to the server.
            client_params: (DEPRECATED) Parameters used for server connection.
            job_id: Job ID.
            program_id: ID of the program this job is for.
            creation_date: Job creation date, in UTC.
            user_callback: (DEPRECATED) User callback function.
            result_decoder: A :class:`ResultDecoder` subclass used to decode job results.
            image: Runtime image used for this job: image_name:tag.
            service: Runtime service.
            session_id: Job ID of the first job in a runtime session.
            tags: Tags assigned to the job.
            version: Primitive version.
        """

        issue_deprecation_msg(
            msg="The RuntimeJob class is deprecated",
            version="0.38.0",
            stacklevel=4,
            remedy="All primitives now return the RuntimeJobV2 class. The major difference between "
            "the two classes is that `Job.status()` is returned as a string in RuntimeJobV2.",
        )

        Job.__init__(self, backend=backend, job_id=job_id)
        BaseRuntimeJob.__init__(
            self,
            backend=backend,
            api_client=api_client,
            client_params=client_params,
            job_id=job_id,
            program_id=program_id,
            service=service,
            creation_date=creation_date,
            user_callback=user_callback,
            result_decoder=result_decoder,
            image=image,
            session_id=session_id,
            tags=tags,
            version=version,
        )
        self._status = JobStatus.INITIALIZING

    def result(  # pylint: disable=arguments-differ
        self,
        timeout: Optional[float] = None,
        decoder: Optional[Type[ResultDecoder]] = None,
    ) -> Any:
        """Return the results of the job.

        Args:
            timeout: Number of seconds to wait for job.
            decoder: A :class:`ResultDecoder` subclass used to decode job results.

        Returns:
            Runtime job result.

        Raises:
            RuntimeJobFailureError: If the job failed.
            RuntimeJobMaxTimeoutError: If the job does not complete within given timeout.
            RuntimeInvalidStateError: If the job was cancelled, and attempting to retrieve result.
        """
        _decoder = decoder or self._final_result_decoder
        self.wait_for_final_state(timeout=timeout)
        if self._status == self.ERROR:
            error_message = self._reason if self._reason else self._error_message
            if self._reason_code == 1305:
                raise RuntimeJobMaxTimeoutError(self._error_message)
            raise RuntimeJobFailureError(f"Unable to retrieve job result. {error_message}")
        if self._status is JobStatus.CANCELLED:
            raise RuntimeInvalidStateError(
                "Unable to retrieve result for job {}. " "Job was cancelled.".format(self.job_id())
            )

        result_raw = self._api_client.job_results(job_id=self.job_id())

        return _decoder.decode(result_raw) if result_raw else None  # type: ignore

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
        self._status = JobStatus.CANCELLED

    def status(self) -> JobStatus:
        """Return the status of the job.

        Returns:
            Status of this job.
        """
        warnings.warn(
            (
                "In a future release of qiskit-ibm-runtime no sooner than 3 months "
                "after the release date of 0.30.0, RuntimeJob.status() will be returned as a string "
                "instead of an instance of `JobStatus`. "
                "To prepare for this change, you can use the idiom "
                "`status.name if isinstance(status, JobStatus) else status`."
            ),
            DeprecationWarning,
            stacklevel=2,
        )
        self._set_status_and_error_message()
        return self._status

    def in_final_state(self) -> bool:
        """Return whether the job is in a final job state such as ``DONE`` or ``ERROR``."""
        return self.status() in self.JOB_FINAL_STATES

    def errored(self) -> bool:
        """Return whether the job has failed."""
        return self.status() == self.ERROR

    def _status_from_job_response(self, response: Dict) -> str:
        """Returns the job status from an API response.

        Args:
            response: Job response from the runtime API.

        Returns:
            Job status.
        """
        mapped_job_status = API_TO_JOB_STATUS[response["state"]["status"].upper()]
        if mapped_job_status == JobStatus.CANCELLED and self._reason_code == 1305:
            mapped_job_status = self.ERROR
        return mapped_job_status

    def submit(self) -> None:
        """Unsupported method.
        Note:
            This method is not supported, please use
            :meth:`~qiskit_ibm_runtime.QiskitRuntimeService.run`
            to submit a job.
        Raises:
            NotImplementedError: Upon invocation.
        """
        raise NotImplementedError(
            "job.submit() is not supported. Please use "
            "QiskitRuntimeService.run() to submit a job."
        )

    def queue_position(self, refresh: bool = False) -> None:  # pylint: disable=unused-argument
        """(DEPRECATED) Return the position of the job in the server queue."""
        warnings.warn(
            "The queue_position() method is deprecated and will be removed in a future release. "
            "The new IBM Quantum Platform does not support this functionality.",
            DeprecationWarning,
            stacklevel=2,
        )

    def queue_info(self) -> None:
        """(DEPRECATED) Return queue information for this job."""
        warnings.warn(
            "The queue_info() method is deprecated and will be removed in a future release. "
            "The new IBM Quantum Platform does not support this functionality.",
            DeprecationWarning,
            stacklevel=2,
        )

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

    def wait_for_final_state(  # pylint: disable=arguments-differ
        self,
        timeout: Optional[float] = None,
    ) -> None:
        """Poll for the job status from the API until the status is in a final state.

        Args:
            timeout: Seconds to wait for the job. If ``None``, wait indefinitely.

        Raises:
            RuntimeJobTimeoutError: If the job does not complete within given timeout.
        """
        try:
            start_time = time.time()
            status = self.status()
            while status not in self.JOB_FINAL_STATES:
                elapsed_time = time.time() - start_time
                if timeout is not None and elapsed_time >= timeout:
                    raise RuntimeJobTimeoutError(
                        f"Timed out waiting for job to complete after {timeout} secs."
                    )
                time.sleep(0.1)
                status = self.status()
        except futures.TimeoutError:
            raise RuntimeJobTimeoutError(
                f"Timed out waiting for job to complete after {timeout} secs."
            )

    def backend(self, timeout: Optional[float] = None) -> Optional[Backend]:
        """Return the backend where this job was executed. Retrieve data again if backend is None.

        Raises:
            IBMRuntimeError: If a network error occurred.
        """
        if not self._backend:  # type: ignore
            self.wait_for_final_state(timeout=timeout)
            try:
                raw_data = self._api_client.job_get(self.job_id())
                if raw_data.get("backend"):
                    self._backend = self._service.backend(raw_data["backend"])
            except RequestsApiError as err:
                raise IBMRuntimeError(f"Failed to get job backend: {err}") from None
        return self._backend
