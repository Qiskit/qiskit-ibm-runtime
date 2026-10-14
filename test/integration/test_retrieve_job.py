# This code is part of Qiskit.
#
# (C) Copyright IBM 2021-2026.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Tests for job functions using real runtime service."""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

import pytest
from qiskit.providers.exceptions import QiskitBackendNotFoundError
from qiskit.providers.jobstatus import JobStatus

from .utils import wait_for_status

if TYPE_CHECKING:
    from collections.abc import Callable

    from qiskit_ibm_runtime import IBMBackend, QiskitRuntimeService, RuntimeJobV2

    from .dependencies import Dependencies


def get_mock_backend_pair(service: QiskitRuntimeService) -> tuple[IBMBackend, IBMBackend]:
    """Return a pair of backends: real backend, mocked backend."""
    backends = service.backends(include_mocks=True)

    try:
        # Find a suitable backend that has a mock backend.
        dry_run_backend = next(
            backend
            for backend in backends
            if backend.name.startswith("mock_") and backend.status().status_msg == "active"
        )
        backend_name = re.sub(r"^[^_]+", "ibm", dry_run_backend.name)
        return service.backend(backend_name), dry_run_backend
    except (StopIteration, QiskitBackendNotFoundError):
        pytest.skip("No backend with corresponding mock backend available.")


class TestIntegrationRetrieveJob:
    """Integration tests for job retrieval functions."""

    def test_retrieve_job_queued(
        self,
        submit_bell_job: Callable[..., RuntimeJobV2],
        dependencies: Dependencies,
    ) -> None:
        """Test retrieving a queued job."""
        service = dependencies.service
        _ = submit_bell_job()
        job = submit_bell_job()
        wait_for_status(job, "QUEUED")
        rjob = service.job(job.job_id())
        assert job.job_id() == rjob.job_id()
        assert "sampler" == rjob.primitive_id

    def test_retrieve_job_running(
        self,
        submit_bell_job: Callable[..., RuntimeJobV2],
        dependencies: Dependencies,
    ) -> None:
        """Test retrieving a running job."""
        service = dependencies.service
        job = submit_bell_job()
        wait_for_status(job, "RUNNING")
        rjob = service.job(job.job_id())
        assert job.job_id() == rjob.job_id()
        assert "sampler" == rjob.primitive_id

    def test_retrieve_job_done(
        self,
        submit_bell_job: Callable[..., RuntimeJobV2],
        dependencies: Dependencies,
    ) -> None:
        """Test retrieving a finished job."""
        service = dependencies.service
        job = submit_bell_job()
        job.wait_for_final_state()
        rjob = service.job(job.job_id())
        assert job.job_id() == rjob.job_id()
        assert "sampler" == rjob.primitive_id

    def test_retrieve_all_jobs(
        self,
        submit_bell_job: Callable[..., RuntimeJobV2],
        dependencies: Dependencies,
    ) -> None:
        """Test retrieving all jobs."""
        service = dependencies.service
        job = submit_bell_job()
        rjobs = service.jobs()
        found = False
        for rjob in rjobs:
            if rjob.job_id() == job.job_id():
                assert job.primitive_id == rjob.primitive_id
                found = True
                break
        assert found

    def test_retrieve_jobs_limit(
        self,
        submit_bell_job: Callable[..., RuntimeJobV2],
        dependencies: Dependencies,
    ) -> None:
        """Test retrieving jobs with limit."""
        service = dependencies.service
        jobs = []
        for _ in range(3):
            jobs.append(submit_bell_job())

        rjobs = service.jobs(limit=2, program_id="sampler")
        assert len(rjobs) == 2

    def test_retrieve_pending_jobs(
        self,
        submit_bell_job: Callable[..., RuntimeJobV2],
        dependencies: Dependencies,
    ) -> None:
        """Test retrieving pending jobs (QUEUED, RUNNING)."""
        service = dependencies.service
        job = submit_bell_job()
        wait_for_status(job, "RUNNING")
        rjobs = service.jobs(pending=True)
        after_status = job.status()
        found = False
        for rjob in rjobs:
            if rjob.job_id() == job.job_id():
                assert job.primitive_id == rjob.primitive_id
                found = True
                break

        assert found or after_status == JobStatus.RUNNING

    def test_retrieve_returned_jobs(
        self,
        submit_bell_job: Callable[..., RuntimeJobV2],
        dependencies: Dependencies,
    ) -> None:
        """Test retrieving returned jobs (COMPLETED, FAILED, CANCELLED)."""
        service = dependencies.service
        job = submit_bell_job()
        job.wait_for_final_state()
        rjobs = service.jobs(pending=False)
        found = False
        for rjob in rjobs:
            if rjob.job_id() == job.job_id():
                assert job.primitive_id == rjob.primitive_id
                found = True
                break
        assert found

    def test_retrieve_jobs_by_program_id(self, dependencies: Dependencies) -> None:
        """Test retrieving jobs by Program ID."""
        service = dependencies.service
        program_id = "sampler"
        jobs = service.jobs(program_id=program_id)
        for job in jobs:
            assert program_id == job.primitive_id

    def test_retrieve_jobs_by_job_tags(
        self,
        submit_bell_job: Callable[..., RuntimeJobV2],
        dependencies: Dependencies,
    ) -> None:
        """Test retrieving jobs by job_tags."""
        service = dependencies.service
        job_tags = ["job_tag_test"]
        job = submit_bell_job(job_tags=job_tags)
        job.wait_for_final_state()
        rjobs = service.jobs(job_tags=job_tags)
        assert job.job_id() in [j.job_id() for j in rjobs]
        rjobs = service.jobs(job_tags=["no_test_tag"])
        assert not rjobs

    def test_retrieve_jobs_by_instance(self, dependencies: Dependencies) -> None:
        """Test retrieving jobs by instance."""
        service = dependencies.service
        instance = dependencies.instance
        rjobs = service.jobs(instance=instance)
        for job in rjobs:
            assert instance == job.instance

    def test_jobs_filter_by_date(
        self,
        submit_bell_job: Callable[..., RuntimeJobV2],
        dependencies: Dependencies,
    ) -> None:
        """Test retrieving jobs by creation date."""
        service = dependencies.service
        current_time = datetime.now(timezone.utc) - timedelta(minutes=1)
        job = submit_bell_job()
        job.wait_for_final_state()
        time_after_job = datetime.now(timezone.utc) + timedelta(minutes=1)
        rjobs = service.jobs(
            created_before=time_after_job, created_after=current_time, pending=False, limit=20
        )
        assert job.job_id() in [j.job_id() for j in rjobs]
        for job in rjobs:
            assert job.creation_date <= time_after_job
            assert job.creation_date >= current_time

    def test_retrieve_jobs_sorted_by_date(
        self,
        submit_bell_job: Callable[..., RuntimeJobV2],
        dependencies: Dependencies,
    ) -> None:
        """Test retrieving jobs sorted by the date."""
        service = dependencies.service
        # Use a unique tag, so that only the jobs submitted by this test are retrieved.
        job_tags = [uuid.uuid4().hex[:16]]
        job = submit_bell_job(job_tags=job_tags)
        job.wait_for_final_state()
        job_2 = submit_bell_job(job_tags=job_tags)
        job_2.wait_for_final_state()

        rjobs = service.jobs(job_tags=job_tags)
        rjobs_ascending = service.jobs(job_tags=job_tags, descending=False)

        # The jobs are returned newest first by default, oldest first when requested.
        assert [rjob.job_id() for rjob in rjobs] == [job_2.job_id(), job.job_id()]
        assert [rjob.job_id() for rjob in rjobs_ascending] == [job.job_id(), job_2.job_id()]

    def test_retrieve_jobs_backend(
        self, backend_test: IBMBackend | None, dependencies: Dependencies
    ) -> None:
        """Test retrieving jobs with backend filter."""
        service = dependencies.service
        backend_name = backend_test.name
        jobs = service.jobs(backend_name=backend_name)
        for job in jobs:
            assert backend_name == job.backend().name

    def test_retrieve_jobs_include_mocks(
        self,
        submit_bell_job: Callable[..., RuntimeJobV2],
        dependencies: Dependencies,
    ) -> None:
        """`service.jobs()` should respect the `include_mocks` flag."""
        service = dependencies.service
        # Skip the test if there are no mock backends.
        _, mock_backend = get_mock_backend_pair(service)

        # Submit job against the mock device.
        job = submit_bell_job(backend_name=mock_backend.name)
        jobs_no_mocks = service.jobs(limit=1)
        jobs_include_mocks = service.jobs(limit=1, include_mocks=True)

        assert jobs_include_mocks[0].job_id() == job.job_id()
        assert jobs_no_mocks[0].job_id() != job.job_id()
