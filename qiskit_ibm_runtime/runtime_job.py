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
import time
import json
import logging
from concurrent import futures
import traceback
import queue
from datetime import datetime
import requests

from qiskit.providers.backend import Backend
from qiskit.providers.jobstatus import JobStatus, JOB_FINAL_STATES
from qiskit.providers.models import BackendProperties
from qiskit.providers.job import JobV1 as Job

# pylint: disable=unused-import,cyclic-import
from qiskit_ibm_provider.utils import utc_to_local
from qiskit_ibm_runtime import qiskit_runtime_service

from .utils.utils import validate_job_tags
from .constants import API_TO_JOB_ERROR_MESSAGE, API_TO_JOB_STATUS, DEFAULT_DECODERS
from .exceptions import (
    IBMApiError,
    RuntimeJobFailureError,
    RuntimeInvalidStateError,
    IBMRuntimeError,
    RuntimeJobTimeoutError,
    RuntimeJobMaxTimeoutError,
)
from .utils.result_decoder import ResultDecoder
from .api.clients import RuntimeClient, RuntimeWebsocketClient, WebsocketClientCloseCode
from .exceptions import IBMError
from .api.exceptions import RequestsApiError
from .api.client_parameters import ClientParameters

logger = logging.getLogger(__name__)


class RuntimeJob(Job):
    """Representation of a runtime program execution.

    A new ``RuntimeJob`` instance is returned when you call
    :meth:`QiskitRuntimeService.run<qiskit_ibm_runtime.QiskitRuntimeService.run>`
    to execute a runtime program, or
    :meth:`QiskitRuntimeService.job<qiskit_ibm_runtime.QiskitRuntimeService.job>`
    to retrieve a previously executed job.

    If the program execution is successful, you can inspect the job's status by
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

    If the program has any interim results, you can use the ``callback``
    parameter of the
    :meth:`~qiskit_ibm_runtime.QiskitRuntimeService.run`
    method to stream the interim results along with the final result.
    Alternatively, you can use the :meth:`stream_results` method to stream
    the results at a later time, but before the job finishes.
    """

    _POISON_PILL = "_poison_pill"
    """Used to inform streaming to stop."""

    _executor = futures.ThreadPoolExecutor(thread_name_prefix="runtime_job")

    def __init__(
        self,
        backend: Backend,
        api_client: RuntimeClient,
        client_params: ClientParameters,
        job_id: str,
        program_id: str,
        service: "qiskit_runtime_service.QiskitRuntimeService",
        params: Optional[Dict] = None,
        creation_date: Optional[str] = None,
        user_callback: Optional[Callable] = None,
        result_decoder: Optional[Union[Type[ResultDecoder], Sequence[Type[ResultDecoder]]]] = None,
        image: Optional[str] = "",
        session_id: Optional[str] = None,
        tags: Optional[List] = None,
    ) -> None:
        """RuntimeJob constructor.

        Args:
            backend: The backend instance used to run this job.
            api_client: Object for connecting to the server.
            client_params: Parameters used for server connection.
            job_id: Job ID.
            program_id: ID of the program this job is for.
            params: Job parameters.
            creation_date: Job creation date, in UTC.
            user_callback: User callback function.
            result_decoder: A :class:`ResultDecoder` subclass used to decode job results.
            image: Runtime image used for this job: image_name:tag.
            service: Runtime service.
            session_id: Job ID of the first job in a runtime session.
            tags: Tags assigned to the job.
        """
        super().__init__(backend=backend, job_id=job_id)
        self._api_client = api_client
        self._interim_results: Optional[Any] = None
        self._params = params or {}
        self._creation_date = creation_date
        self._program_id = program_id
        self._status = JobStatus.INITIALIZING
        self._reason: Optional[str] = None
        self._error_message: Optional[str] = None
        self._image = image
        self._final_interim_results = False
        self._service = service
        self._session_id = session_id
        self._tags = tags
        self._usage_estimation: Dict[str, Any] = {}

        decoder = result_decoder or DEFAULT_DECODERS.get(program_id, None) or ResultDecoder
        if isinstance(decoder, Sequence):
            self._interim_result_decoder, self._final_result_decoder = decoder
        else:
            self._interim_result_decoder = self._final_result_decoder = decoder

        # Used for streaming
        self._ws_client_future = None  # type: Optional[futures.Future]
        self._result_queue = queue.Queue()  # type: queue.Queue
        self._ws_client = RuntimeWebsocketClient(
            websocket_url=client_params.get_runtime_api_base_url().replace("https", "wss"),
            client_params=client_params,
            job_id=job_id,
            message_queue=self._result_queue,
        )

        if user_callback is not None:
            self.stream_results(user_callback)

    def _download_external_result(self, response: Any) -> Any:
        """Download result from external URL.

        Args:
            response: Response to check for url keyword, if available, download result from given URL
        """
        try:
            result_url_json = json.loads(response)
            if "url" in result_url_json:
                url = result_url_json["url"]
                result_response = requests.get(url, timeout=10)
                return result_response.text
            return response
        except json.JSONDecodeError:
            return response

    def interim_results(self, decoder: Optional[Type[ResultDecoder]] = None) -> Any:
        """Return the interim results of the job.

        Args:
            decoder: A :class:`ResultDecoder` subclass used to decode interim results.

        Returns:
            Runtime job interim results.

        Raises:
            RuntimeJobFailureError: If the job failed.
        """
        if not self._final_interim_results:
            _decoder = decoder or self._interim_result_decoder
            interim_results_raw = self._api_client.job_interim_results(job_id=self.job_id())
            self._interim_results = _decoder.decode(interim_results_raw)
            if self.status() in JOB_FINAL_STATES:
                self._final_interim_results = True
        return self._interim_results

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
        if self._status == JobStatus.ERROR:
            error_message = self._reason if self._reason else self._error_message
            if self._reason == "RAN TOO LONG":
                raise RuntimeJobMaxTimeoutError(error_message)
            raise RuntimeJobFailureError(f"Unable to retrieve job result. {error_message}")
        if self._status is JobStatus.CANCELLED:
            raise RuntimeInvalidStateError(
                "Unable to retrieve result for job {}. " "Job was cancelled.".format(self.job_id())
            )

        result_raw = self._download_external_result(
            self._api_client.job_results(job_id=self.job_id())
        )

        return _decoder.decode(result_raw) if result_raw else None

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
        self.cancel_result_streaming()
        self._status = JobStatus.CANCELLED

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

    def status(self) -> JobStatus:
        """Return the status of the job.

        Returns:
            Status of this job.
        """
        self._set_status_and_error_message()
        return self._status

    def error_message(self) -> Optional[str]:
        """Returns the reason if the job failed.

        Returns:
            Error message string or ``None``.
        """
        self._set_status_and_error_message()
        return self._error_message

    def wait_for_final_state(  # pylint: disable=arguments-differ
        self,
        timeout: Optional[float] = None,
    ) -> None:
        """Use the websocket server to wait for the final the state of a job.

        The server will remain open if the job is still running and the connection will
        be terminated once the job completes. Then update and return the status of the job.

        Args:
            timeout: Seconds to wait for the job. If ``None``, wait indefinitely.

        Raises:
            RuntimeJobTimeoutError: If the job does not complete within given timeout.
        """
        try:
            start_time = time.time()
            if self._status not in JOB_FINAL_STATES and not self._is_streaming():
                self._ws_client_future = self._executor.submit(self._start_websocket_client)
            if self._is_streaming():
                self._ws_client_future.result(timeout)
            # poll for status after stream has closed until status is final
            # because status doesn't become final as soon as stream closes
            status = self.status()
            while status not in JOB_FINAL_STATES:
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

    def stream_results(
        self, callback: Callable, decoder: Optional[Type[ResultDecoder]] = None
    ) -> None:
        """Start streaming job results.

        Args:
            callback: Callback function to be invoked for any interim results and final result.
                The callback function will receive 2 positional parameters:

                    1. Job ID
                    2. Job result.

            decoder: A :class:`ResultDecoder` subclass used to decode job results.

        Raises:
            RuntimeInvalidStateError: If a callback function is already streaming results or
                if the job already finished.
        """
        if self._status in JOB_FINAL_STATES:
            raise RuntimeInvalidStateError("Job already finished.")
        if self._is_streaming():
            raise RuntimeInvalidStateError("A callback function is already streaming results.")
        self._ws_client_future = self._executor.submit(self._start_websocket_client)
        self._executor.submit(
            self._stream_results,
            result_queue=self._result_queue,
            user_callback=callback,
            decoder=decoder,
        )

    def cancel_result_streaming(self) -> None:
        """Cancel result streaming."""
        if not self._is_streaming():
            return
        self._ws_client.disconnect(WebsocketClientCloseCode.CANCEL)

    def logs(self) -> str:
        """Return job logs.

        Note:
            Job logs are only available after the job finishes.

        Returns:
            Job logs, including standard output and error.

        Raises:
            IBMRuntimeError: If a network error occurred.
        """
        if self.status() not in JOB_FINAL_STATES:
            logger.warning("Job logs are only available after the job finishes.")
        try:
            return self._api_client.job_logs(self.job_id())
        except RequestsApiError as err:
            if err.status_code == 404:
                return ""
            raise IBMRuntimeError(f"Failed to get job logs: {err}") from None

    def metrics(self) -> Dict[str, Any]:
        """Return job metrics.

        Returns:
            Job metrics, which includes timestamp information.

        Raises:
            IBMRuntimeError: If a network error occurred.
        """
        try:
            return self._api_client.job_metadata(self.job_id())
        except RequestsApiError as err:
            raise IBMRuntimeError(f"Failed to get job metadata: {err}") from None

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

    def _set_status_and_error_message(self) -> None:
        """Fetch and set status and error message."""
        if self._status not in JOB_FINAL_STATES:
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
            reason_code = job_response["state"].get("reason_code")
            if reason:
                # TODO remove this in https://github.com/Qiskit/qiskit-ibm-runtime/issues/989
                if reason.upper() == "RAN TOO LONG":
                    self._reason = reason.upper()
                else:
                    self._reason = reason
                if reason_code:
                    self._reason = f"Error code {reason_code}; {self._reason}"
            self._status = self._status_from_job_response(job_response)
        except KeyError:
            raise IBMError(f"Unknown status: {job_response['state']['status']}")

    def _set_error_message(self, job_response: Dict) -> None:
        """Set error message if the job failed.

        Args:
            job_response: Job response from runtime API.
        """
        if self._status == JobStatus.ERROR:
            self._error_message = self._error_msg_from_job_response(job_response)
        else:
            self._error_message = None

    def _error_msg_from_job_response(self, response: Dict) -> str:
        """Returns the error message from an API response.

        Args:
            response: Job response from the runtime API.

        Returns:
            Error message.
        """
        status = response["state"]["status"].upper()

        job_result_raw = self._download_external_result(
            self._api_client.job_results(job_id=self.job_id())
        )
        index = job_result_raw.rfind("Traceback")
        if index != -1:
            job_result_raw = job_result_raw[index:]

        if status == "CANCELLED" and self._reason == "RAN TOO LONG":
            error_msg = API_TO_JOB_ERROR_MESSAGE["CANCELLED - RAN TOO LONG"]
            return error_msg.format(self.job_id(), job_result_raw)
        else:
            error_msg = API_TO_JOB_ERROR_MESSAGE["FAILED"]
            return error_msg.format(self.job_id(), self._reason or job_result_raw)

    def _status_from_job_response(self, response: Dict) -> str:
        """Returns the job status from an API response.

        Args:
            response: Job response from the runtime API.

        Returns:
            Job status.
        """
        mapped_job_status = API_TO_JOB_STATUS[response["state"]["status"].upper()]
        if mapped_job_status == JobStatus.CANCELLED and self._reason == "RAN TOO LONG":
            mapped_job_status = JobStatus.ERROR
        return mapped_job_status

    def _is_streaming(self) -> bool:
        """Return whether job results are being streamed.

        Returns:
            Whether job results are being streamed.
        """
        if self._ws_client_future is None:
            return False

        if self._ws_client_future.done():
            return False

        return True

    def _start_websocket_client(self) -> None:
        """Start websocket client to stream results."""
        try:
            logger.debug("Start websocket client for job %s", self.job_id())
            self._ws_client.job_results()
        except Exception:  # pylint: disable=broad-except
            logger.warning(
                "An error occurred while streaming results from the server for job %s:\n%s",
                self.job_id(),
                traceback.format_exc(),
            )
        finally:
            self._result_queue.put_nowait(self._POISON_PILL)

    def _stream_results(
        self,
        result_queue: queue.Queue,
        user_callback: Callable,
        decoder: Optional[Type[ResultDecoder]] = None,
    ) -> None:
        """Stream results.

        Args:
            result_queue: Queue used to pass websocket messages.
            user_callback: User callback function.
            decoder: A :class:`ResultDecoder` (sub)class used to decode job results.
        """
        logger.debug("Start result streaming for job %s", self.job_id())
        _decoder = decoder or self._interim_result_decoder
        while True:
            try:
                response = result_queue.get()
                if response == self._POISON_PILL:
                    self._empty_result_queue(result_queue)
                    return

                response = self._download_external_result(response)

                user_callback(self.job_id(), _decoder.decode(response))
            except Exception:  # pylint: disable=broad-except
                logger.warning(
                    "An error occurred while streaming results for job %s:\n%s",
                    self.job_id(),
                    traceback.format_exc(),
                )

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
        if not self._params:
            response = self._api_client.job_get(job_id=self.job_id())
            self._params = response.get("params", {})
        return self._params

    @property
    def program_id(self) -> str:
        """Program ID.

        Returns:
            ID of the program this job is for.
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
            Job ID of the first job in a runtime session.
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
        """Return the usage estimation infromation for this job.

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
