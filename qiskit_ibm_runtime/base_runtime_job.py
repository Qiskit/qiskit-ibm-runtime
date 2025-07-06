# This code is part of Qiskit.
#
# (C) Copyright IBM 2024.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Base runtime job class."""

from abc import ABC, abstractmethod
from typing import Any, Optional, Callable, Dict, Type, Union, Sequence, List, Tuple
import logging
from concurrent import futures
import queue
from datetime import datetime

from qiskit.providers.backend import Backend
from qiskit.providers.jobstatus import JobStatus as RuntimeJobStatus

# pylint: disable=unused-import,cyclic-import

from qiskit_ibm_runtime import qiskit_runtime_service

from .utils import utc_to_local, validate_job_tags
from .constants import DEFAULT_DECODERS, API_TO_JOB_ERROR_MESSAGE
from .exceptions import (
    IBMError,
    IBMApiError,
    IBMRuntimeError,
)
from .utils.result_decoder import ResultDecoder
from .utils.deprecation import issue_deprecation_msg
from .models import BackendProperties
from .api.clients import RuntimeClient
from .api.exceptions import RequestsApiError
from .api.client_parameters import ClientParameters

logger = logging.getLogger(__name__)


class BaseRuntimeJob(ABC):
    """Base Runtime Job class."""

    _executor = futures.ThreadPoolExecutor(thread_name_prefix="runtime_job")

    JOB_FINAL_STATES: Tuple[Any, ...] = ()
    ERROR: Union[str, RuntimeJobStatus] = None

    def __init__(
        self,
        backend: Backend,
        api_client: RuntimeClient,
        job_id: str,
        program_id: str,
        service: "qiskit_runtime_service.QiskitRuntimeService",
        client_params: ClientParameters = None,
        creation_date: Optional[str] = None,
        user_callback: Optional[Callable] = None,
        result_decoder: Optional[Union[Type[ResultDecoder], Sequence[Type[ResultDecoder]]]] = None,
        image: Optional[str] = "",
        session_id: Optional[str] = None,
        tags: Optional[List] = None,
        version: Optional[int] = None,
        private: Optional[bool] = False,
    ) -> None:
        """RuntimeJob constructor.

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
            private: Marks job as private.
        """
        self._backend = backend
        self._job_id = job_id
        self._api_client = api_client
        self._creation_date = creation_date
        self._program_id = program_id
        self._reason: Optional[str] = None
        self._reason_code: Optional[int] = None
        self._error_message: Optional[str] = None
        self._image = image
        self._service = service
        self._session_id = session_id
        self._tags = tags
        self._usage_estimation: Dict[str, Any] = {}
        self._version = version
        self._queue_info = None
        self._status: Union[RuntimeJobStatus, str] = None
        self._private = private

        decoder = result_decoder or DEFAULT_DECODERS.get(program_id, None) or ResultDecoder
        if isinstance(decoder, Sequence):
            _, self._final_result_decoder = decoder
        else:
            self._final_result_decoder = decoder

        if user_callback or client_params:
            issue_deprecation_msg(
                msg="The job class parameters 'user_callback' and 'client_params' are deprecated",
                version="0.38.0",
                remedy="These parameters will have no effect since interim "
                "results streaming was removed in a previous release.",
            )

    @property
    def private(self) -> bool:
        """Returns a boolean indicating whether or not the job is private."""
        return self._private

    def job_id(self) -> str:
        """Return a unique id identifying the job."""
        return self._job_id

    def usage(self) -> float:
        """Return job usage in seconds."""
        try:
            metrics = self._api_client.job_metadata(self.job_id())
            return metrics.get("usage", {}).get("quantum_seconds")
        except RequestsApiError as err:
            raise IBMRuntimeError(f"Failed to get job metadata: {err}") from None

    def metrics(self) -> Dict[str, Any]:
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

    def update_tags(self, new_tags: List[str]) -> List[str]:
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
                "tags for job {}. The tags were not updated for "
                "the job.".format(self.job_id())
            )

    def properties(self, refresh: bool = False) -> Optional[BackendProperties]:
        """Return the backend properties for this job.

        Args:
            refresh: If ``True``, re-query the server for the backend properties.
                Otherwise, return a cached version.

        Returns:
            The backend properties used for this job, at the time the job was run,
            or ``None`` if properties are not available.
        """

        return self._backend.properties(refresh, self.creation_date)

    def error_message(self) -> Optional[str]:
        """Returns the reason if the job failed.

        Returns:
            Error message string or ``None``.
        """
        self._set_status_and_error_message()
        return self._error_message

    def _set_status_and_error_message(self) -> None:
        """Fetch and set status and error message."""
        if self._status not in self.JOB_FINAL_STATES:
            response = self._api_client.job_get(job_id=self.job_id())
            self._set_status(response)
            self._set_error_message(response)

    def _set_status(self, job_response: Dict) -> None:
        """Set status.

        Args:
            job_response: Job response from runtime API.

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

    def _set_error_message(self, job_response: Dict) -> None:
        """Set error message if the job failed.

        Args:
            job_response: Job response from runtime API.
        """
        if self._status == self.ERROR:
            self._error_message = self._error_msg_from_job_response(job_response)
        else:
            self._error_message = None

    @abstractmethod
    def _status_from_job_response(self, response: Dict) -> str:
        """Returns the job status from an API response."""
        return response["state"]["status"].upper()

    def _error_msg_from_job_response(self, response: Dict) -> str:
        """Returns the error message from an API response.

        Args:
            response: Job response from the runtime API.

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

    @staticmethod
    def _empty_result_queue(result_queue: queue.Queue) -> None:
        """Empty the result queue.

        Args:
            result_queue: Result queue to empty.
        """
        try:
            while True:
                result_queue.get_nowait()
        except queue.Empty:
            pass

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}('{self._job_id}', '{self._program_id}')>"

    @property
    def image(self) -> str:
        """Return the runtime image used for the job.

        Returns:
            Runtime image: image_name:tag or "" if the default
            image is used.
        """
        return self._image

    @property
    def inputs(self) -> Dict:
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
    def creation_date(self) -> Optional[datetime]:
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
    def tags(self) -> List:
        """Job tags.

        Returns:
            Tags assigned to the job that can be used for filtering.
        """
        return self._tags

    @property
    def usage_estimation(self) -> Dict[str, Any]:
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
    def instance(self) -> Optional[str]:
        """Return the IBM Cloud instance CRN."""
        return self._backend._instance

    @abstractmethod
    def in_final_state(self) -> bool:
        """Return whether the job is in a final job state such as ``DONE`` or ``ERROR``."""
        pass

    @abstractmethod
    def errored(self) -> bool:
        """Return whether the job has failed."""
        pass
