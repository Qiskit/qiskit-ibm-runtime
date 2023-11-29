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

from typing import Optional, Dict, Union, List, Type, Sequence, Any

from qiskit.primitives.primitive_job import PrimitiveJob
from qiskit.primitives.base.base_primitive import BasePrimitive
from qiskit.providers import JobError, JobStatus, JobV1
from qiskit.providers.fake_provider import FakeBackendV2 as FakeBackend

from .utils.result_decoder import ResultDecoder


class FakeRuntimeJob(JobV1):
    """Representation of a runtime program execution on a simulator."""

    def __init__(
        self,
        primitive_job: PrimitiveJob,
        backend: FakeBackend,
        job_id: str,
        program_id: str,
        service: "qiskit_runtime_service.QiskitRuntimeService",
        params: Optional[Dict] = None,
        creation_date: Optional[str] = None,
        # user_callback: Optional[Callable] = None,
        # result_decoder: Optional[Union[Type[ResultDecoder], Sequence[Type[ResultDecoder]]]] = None,
        # tags: Optional[List] = None,
    ) -> None:
        """FakeRuntimeJob constructor."""
        super().__init__(backend=backend, job_id=job_id)
        self._primitive_job = primitive_job
        self._job_id = job_id
        self._params = params or {}
        self._program_id = program_id

    def result(self) -> Any:
        """Return the results of the job."""
        return self._primitive_job.result()

    def cancel(self):
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
