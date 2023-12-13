# This code is part of Qiskit.
#
# (C) Copyright IBM 2023.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Qiskit fake runtime job."""

from typing import Optional, Dict, Any, List
from datetime import datetime

from qiskit.primitives.primitive_job import PrimitiveJob
from qiskit.providers import JobStatus, JobV1
from qiskit.providers.fake_provider import FakeBackendV2 as FakeBackend

# pylint: disable=cyclic-import
# from .qiskit_runtime_service import QiskitRuntimeService


class FakeRuntimeJob(JobV1):
    """Representation of a runtime program execution on a simulator."""

    def __init__(
        self,
        primitive_job: PrimitiveJob,
        backend: FakeBackend,
        job_id: str,
        program_id: str,
        params: Optional[Dict] = None,
        creation_date: Optional[str] = None,
        tags: Optional[List] = None,
    ) -> None:
        """FakeRuntimeJob constructor."""
        super().__init__(backend=backend, job_id=job_id)
        self._primitive_job = primitive_job
        self._job_id = job_id
        self._params = params or {}
        self._program_id = program_id
        self._creation_date = creation_date
        self._tags = tags

    def result(self) -> Any:
        """Return the results of the job."""
        return self._primitive_job.result()

    def cancel(self) -> None:
        self._primitive_job.cancel()

    def status(self) -> JobStatus:
        return self._primitive_job.status()

    @property
    def inputs(self) -> Dict:
        """Job input parameters.

        Returns:
            Input parameters used in this job.
        """
        return self._params

    @property
    def creation_date(self) -> Optional[datetime]:
        """Job creation date in local time.

        Returns:
            The job creation date as a datetime object, in local time, or
            ``None`` if creation date is not available.
        """
        return self._creation_date

    @property
    def tags(self) -> List:
        """Job tags.

        Returns:
            Tags assigned to the job that can be used for filtering.
        """
        return self._tags

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
