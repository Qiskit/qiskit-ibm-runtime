# This code is part of Qiskit.
#
# (C) Copyright IBM 2021.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Fake RuntimeClient."""

import base64
import json
import time
import uuid
from datetime import timezone, datetime as python_datetime
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, Dict, Any, List

from qiskit.providers.exceptions import QiskitBackendNotFoundError

from qiskit_ibm_provider.utils.hgp import from_instance_format
from qiskit_ibm_runtime.api.exceptions import RequestsApiError
from qiskit_ibm_runtime.utils import RuntimeEncoder

from .fake_api_backend import FakeApiBackend, FakeApiBackendSpecs


class BaseFakeProgram:
    """Base class for faking a program."""

    def __init__(
        self,
        program_id,
        name,
        data,
        cost,
        description,
        backend_requirements=None,
        parameters=None,
        return_values=None,
        interim_results=None,
        is_public=False,
    ):
        """Initialize a fake program."""
        self._id = program_id
        self._name = name
        self._data = data
        self._cost = cost
        self._description = description
        self._backend_requirements = backend_requirements
        self._parameters = parameters
        self._return_values = return_values
        self._interim_results = interim_results
        self._is_public = is_public

    def to_dict(self, include_data=False):
        """Convert this program to a dictionary format."""
        out = {
            "id": self._id,
            "name": self._name,
            "cost": self._cost,
            "description": self._description,
            "is_public": self._is_public,
            "creation_date": "2021-09-13T17:27:42Z",
            "update_date": "2021-09-14T19:25:32Z",
        }
        if include_data:
            out["data"] = base64.standard_b64decode(self._data).decode()
        out["spec"] = {}
        if self._backend_requirements:
            out["spec"]["backend_requirements"] = self._backend_requirements
        if self._parameters:
            out["spec"]["parameters"] = self._parameters
        if self._return_values:
            out["spec"]["return_values"] = self._return_values
        if self._interim_results:
            out["spec"]["interim_results"] = self._interim_results

        return out


class BaseFakeRuntimeJob:
    """Base class for faking a runtime job."""

    _job_progress = ["QUEUED", "RUNNING", "COMPLETED"]

    _executor = ThreadPoolExecutor()  # pylint: disable=bad-option-value,consider-using-with

    def __init__(
        self,
        job_id,
        program_id,
        hub,
        group,
        project,
        backend_name,
        final_status,
        params,
        image,
        job_tags=None,
        log_level=None,
        session_id=None,
        max_execution_time=None,
        start_session=None,
        channel_strategy=None,
    ):
        """Initialize a fake job."""
        self._job_id = job_id
        self._status = final_status or "QUEUED"
        self._reason: Optional[str] = None
        self._program_id = program_id
        self._hub = hub
        self._group = group
        self._project = project
        self._backend_name = backend_name
        self._params = params
        self._image = image
        self._interim_results = json.dumps("foo")
        self._job_tags = job_tags
        self.log_level = log_level
        self._session_id = session_id
        self._max_execution_time = max_execution_time
        self._start_session = start_session
        self._creation_date = python_datetime.now(timezone.utc)
        if final_status is None:
            self._future = self._executor.submit(self._auto_progress)
            self._result = None
        elif final_status == "COMPLETED":
            self._result = json.dumps("foo")
        self._final_status = final_status
        self._channel_strategy = channel_strategy

    def _auto_progress(self):
        """Automatically update job status."""
        for status in self._job_progress:
            time.sleep(0.5)
            self._status = status

        if self._status == "COMPLETED":
            self._result = json.dumps("foo")

    def to_dict(self):
        """Convert to dictionary format."""
        return {
            "id": self._job_id,
            "hub": self._hub,
            "group": self._group,
            "project": self._project,
            "backend": self._backend_name,
            "state": {"status": self._status, "reason": self._reason},
            "params": self._params,
            "program": {"id": self._program_id},
            "image": self._image,
        }

    def result(self):
        """Return job result."""
        return self._result

    def interim_results(self):
        """Return job interim results."""
        return self._interim_results

    def status(self):
        """Return job status."""
        return self._status


class FailedRuntimeJob(BaseFakeRuntimeJob):
    """Class for faking a failed runtime job."""

    _job_progress = ["QUEUED", "RUNNING", "FAILED"]

    def _auto_progress(self):
        """Automatically update job status."""
        super()._auto_progress()

        if self._status == "FAILED":
            self._result = "Kaboom!"


class FailedRanTooLongRuntimeJob(BaseFakeRuntimeJob):
    """Class for faking a failed runtime job."""

    _job_progress = ["QUEUED", "RUNNING", "CANCELLED"]

    def _auto_progress(self):
        """Automatically update job status."""
        super()._auto_progress()

        if self._status == "CANCELLED":
            self._reason = "RAN TOO LONG"
            self._result = "Kaboom!"


class CancelableRuntimeJob(BaseFakeRuntimeJob):
    """Class for faking a cancelable runtime job."""

    _job_progress = ["QUEUED", "RUNNING"]

    def __init__(self, *args, **kwargs):
        """Initialize a cancellable job."""
        super().__init__(*args, **kwargs)
        self._cancelled = False

    def cancel(self):
        """Cancel the job."""
        self._future.cancel()
        self._cancelled = True

    def to_dict(self):
        """Convert to dictionary format."""
        data = super().to_dict()
        if self._cancelled:
            data["state"]["status"] = "CANCELLED"
        return data


class CustomResultRuntimeJob(BaseFakeRuntimeJob):
    """Class for using custom job result."""

    custom_result = "bar"

    def _auto_progress(self):
        """Automatically update job status."""
        super()._auto_progress()

        if self._status == "COMPLETED":
            self._result = json.dumps(self.custom_result, cls=RuntimeEncoder)


class TimedRuntimeJob(BaseFakeRuntimeJob):
    """Class for a job that runs for the input seconds."""

    def __init__(self, **kwargs):
        self._runtime = kwargs.pop("run_time")
        super().__init__(**kwargs)

    def _auto_progress(self):
        self._status = "RUNNING"
        time.sleep(self._runtime)
        self._status = "COMPLETED"

        if self._status == "COMPLETED":
            self._result = json.dumps("foo")


class BaseFakeRuntimeClient:
    """Base class for faking the runtime client."""

    def __init__(
        self,
        job_classes=None,
        final_status=None,
        job_kwargs=None,
        backend_client=None,
        channel="ibm_quantum",
        num_backends=2,
        backend_specs=None,
    ):
        """Initialize a fake runtime client."""
        # pylint: disable=unused-argument
        self._programs = {}
        self._jobs = {}
        self._job_classes = job_classes or []
        self._final_status = final_status
        self._job_kwargs = job_kwargs or {}
        self._channel = channel
        self.session_time = 0

        # Setup the available backends
        if not backend_specs:
            backend_specs = [
                FakeApiBackendSpecs(backend_name=f"backend{idx}") for idx in range(num_backends)
            ]
        self._backends = [FakeApiBackend(specs) for specs in backend_specs]

    def set_job_classes(self, classes):
        """Set job classes to use."""
        if not isinstance(classes, list):
            classes = [classes]
        self._job_classes = classes

    def set_final_status(self, final_status):
        """Set job status to passed in final status instantly."""
        self._final_status = final_status

    def list_programs(self, limit, skip):
        """List all programs."""
        programs = []
        for prog in self._programs.values():
            programs.append(prog.to_dict())
        return {"programs": programs[skip : limit + skip], "count": len(self._programs)}

    def program_create(
        self,
        program_data,
        name,
        description,
        max_execution_time,
        spec=None,
        is_public=False,
    ):
        """Create a program."""
        program_id = name
        if program_id in self._programs:
            raise RequestsApiError("Program already exists.", status_code=409)
        backend_requirements = spec.get("backend_requirements", None)
        parameters = spec.get("parameters", None)
        return_values = spec.get("return_values", None)
        interim_results = spec.get("interim_results", None)
        self._programs[program_id] = BaseFakeProgram(
            program_id=program_id,
            name=name,
            data=program_data,
            cost=max_execution_time,
            description=description,
            backend_requirements=backend_requirements,
            parameters=parameters,
            return_values=return_values,
            interim_results=interim_results,
            is_public=is_public,
        )
        return {"id": program_id}

    def program_update(
        self,
        program_id: str,
        program_data: str = None,
        name: str = None,
        description: str = None,
        max_execution_time: int = None,
        spec: Optional[Dict] = None,
    ) -> None:
        """Update a program."""
        program = self._get_program(program_id)
        program._data = program_data or program._data
        program._name = name or program._name
        program._description = description or program._description
        program._cost = max_execution_time or program._cost
        if spec:
            program._backend_requirements = (
                spec.get("backend_requirements") or program._backend_requirements
            )
            program._parameters = spec.get("parameters") or program._parameters
            program._return_values = spec.get("return_values") or program._return_values
            program._interim_results = spec.get("interim_results") or program._interim_results

    def program_get(self, program_id: str) -> Dict[str, Any]:
        """Return a specific program."""
        if program_id not in self._programs:
            raise RequestsApiError("Program not found", status_code=404)
        return self._programs[program_id].to_dict(include_data=True)

    def program_run(
        self,
        program_id: str,
        backend_name: Optional[str],
        params: Dict,
        image: str,
        hgp: Optional[str],
        log_level: Optional[str],
        session_id: Optional[str] = None,
        job_tags: Optional[List[str]] = None,
        max_execution_time: Optional[int] = None,
        start_session: Optional[bool] = None,
        session_time: Optional[int] = None,
        channel_strategy: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Run the specified program."""
        _ = self._get_program(program_id)
        job_id = uuid.uuid4().hex
        job_cls = self._job_classes.pop(0) if len(self._job_classes) > 0 else BaseFakeRuntimeJob
        if hgp:
            hub, group, project = from_instance_format(hgp)
        else:
            hub = group = project = None

        if backend_name is None:
            backend_name = self.list_backends()[0]

        if session_id is None:
            session_id = job_id

        job = job_cls(
            job_id=job_id,
            program_id=program_id,
            hub=hub,
            group=group,
            project=project,
            backend_name=backend_name,
            params=params,
            final_status=self._final_status,
            image=image,
            log_level=log_level,
            session_id=session_id,
            job_tags=job_tags,
            max_execution_time=max_execution_time,
            start_session=start_session,
            channel_strategy=channel_strategy,
            **self._job_kwargs,
        )
        self.session_time = session_time
        self._jobs[job_id] = job
        return {"id": job_id, "backend": backend_name}

    def program_delete(self, program_id: str) -> None:
        """Delete the specified program."""
        self._get_program(program_id)
        del self._programs[program_id]

    def job_get(self, job_id: str, exclude_params: bool = None) -> Any:
        """Get the specific job."""
        return self._get_job(job_id, exclude_params).to_dict()

    def jobs_get(
        self,
        limit=None,
        skip=None,
        backend_name=None,
        pending=None,
        program_id=None,
        hub=None,
        group=None,
        project=None,
        job_tags=None,
        session_id=None,
        created_after=None,
        created_before=None,
        descending=True,
    ):
        """Get all jobs."""
        pending_statuses = ["QUEUED", "RUNNING"]
        returned_statuses = ["COMPLETED", "FAILED", "CANCELLED"]
        limit = limit or len(self._jobs)
        skip = skip or 0
        jobs = list(self._jobs.values())

        if backend_name:
            jobs = [job for job in jobs if job._backend == backend_name]
        if pending is not None:
            job_status_list = pending_statuses if pending else returned_statuses
            jobs = [job for job in jobs if job._status in job_status_list]
        if program_id:
            jobs = [job for job in jobs if job._program_id == program_id]
        if all([hub, group, project]):
            jobs = [
                job
                for job in jobs
                if job._hub == hub and job._group == group and job._project == project
            ]
        if job_tags:
            jobs = [job for job in jobs if job._job_tags == job_tags]
        if session_id:
            jobs = [job for job in jobs if job._session_id == session_id]
        if created_after:
            jobs = [job for job in jobs if job._creation_date >= created_after]
            jobs = [job for job in jobs if job._creation_date <= created_before]

        count = len(jobs)
        jobs = jobs[skip : limit + skip]
        if descending is False:
            jobs.reverse()

        return {"jobs": [job.to_dict() for job in jobs], "count": count}

    def set_program_visibility(self, program_id: str, public: bool) -> None:
        """Sets a program's visibility.

        Args:
            program_id: Program ID.
            public: If ``True``, make the program visible to all.
                If ``False``, make the program visible to just your account.
        """
        program = self._get_program(program_id)
        program._is_public = public

    def job_results(self, job_id):
        """Get the results of a program job."""
        return self._get_job(job_id).result()

    def job_interim_results(self, job_id):
        """Get the interim results of a program job."""
        return self._get_job(job_id).interim_results()

    def job_cancel(self, job_id):
        """Cancel the job."""
        self._get_job(job_id).cancel()

    def job_delete(self, job_id):
        """Delete the job."""
        self._get_job(job_id)
        del self._jobs[job_id]

    def wait_for_final_state(self, job_id):
        """Wait for the final state of a program job."""
        final_states = ["COMPLETED", "FAILED", "CANCELLED", "CANCELLED - RAN TOO LONG"]
        status = self._get_job(job_id).status()
        while status not in final_states:
            status = self._get_job(job_id).status()

    def _get_program(self, program_id):
        """Get program."""
        if program_id not in self._programs:
            raise RequestsApiError("Program not found", status_code=404)
        return self._programs[program_id]

    # pylint: disable=unused-argument
    def _get_job(self, job_id: str, exclude_params: bool = None) -> Any:
        """Get job."""
        if job_id not in self._jobs:
            raise RequestsApiError("Job not found", status_code=404)
        return self._jobs[job_id]

    # pylint: disable=unused-argument
    def list_backends(
        self, hgp: Optional[str] = None, channel_strategy: Optional[str] = None
    ) -> List[str]:
        """Return IBM backends available for this service instance."""
        return [back.name for back in self._backends if back.has_access(hgp)]

    def backend_configuration(self, backend_name: str) -> Dict[str, Any]:
        """Return the configuration a backend."""
        return self._find_backend(backend_name).configuration

    def backend_status(self, backend_name: str) -> Dict[str, Any]:
        """Return the status of a backend."""
        return self._find_backend(backend_name).status

    def backend_properties(self, backend_name: str, datetime: Any = None) -> Dict[str, Any]:
        """Return the properties of a backend."""
        if datetime:
            raise NotImplementedError("'datetime' is not supported.")
        return self._find_backend(backend_name).properties

    def backend_pulse_defaults(self, backend_name: str) -> Dict[str, Any]:
        """Return the pulse defaults of a backend."""
        return self._find_backend(backend_name).defaults

    def _find_backend(self, backend_name):
        for back in self._backends:
            if back.name == backend_name:
                return back
        raise QiskitBackendNotFoundError(f"Backend {backend_name} not found")
