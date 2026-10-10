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
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING
from unittest import SkipTest

from qiskit.providers.exceptions import QiskitBackendNotFoundError
from qiskit.providers.jobstatus import JobStatus

from ..utils import wait_for_status
from .case import IBMIntegrationJobTestCase

if TYPE_CHECKING:
    from qiskit_ibm_runtime import IBMBackend, QiskitRuntimeService


def get_mock_backend_pair(service: QiskitRuntimeService) -> tuple[IBMBackend, IBMBackend]:
    """Return a pair of backends: real backend, mocked backend.

    Raises:
        SkiTest: if no backend that has a corresponding mock backend is available.
    """
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
        raise SkipTest("No backend with corresponding mock backend available.")


class TestIntegrationRetrieveJob(IBMIntegrationJobTestCase):
    """Integration tests for job retrieval functions."""

    def test_retrieve_job_queued(self):
        """Test retrieving a queued job."""
        service = self.service
        _ = self.submit_bell_job(service)
        job = self.submit_bell_job(service)
        wait_for_status(job, "QUEUED")
        rjob = service.job(job.job_id())
        assert job.job_id() == rjob.job_id()
        assert "sampler" == rjob.primitive_id

    def test_retrieve_job_running(self):
        """Test retrieving a running job."""
        service = self.service
        job = self.submit_bell_job(service)
        wait_for_status(job, "RUNNING")
        rjob = service.job(job.job_id())
        assert job.job_id() == rjob.job_id()
        assert "sampler" == rjob.primitive_id

    def test_retrieve_job_done(self):
        """Test retrieving a finished job."""
        service = self.service
        job = self.submit_bell_job(service)
        job.wait_for_final_state()
        rjob = service.job(job.job_id())
        assert job.job_id() == rjob.job_id()
        assert "sampler" == rjob.primitive_id

    def test_retrieve_all_jobs(self):
        """Test retrieving all jobs."""
        service = self.service
        job = self.submit_bell_job(service)
        rjobs = service.jobs()
        found = False
        for rjob in rjobs:
            if rjob.job_id() == job.job_id():
                assert job.primitive_id == rjob.primitive_id
                found = True
                break
        assert found

    def test_retrieve_jobs_limit(self):
        """Test retrieving jobs with limit."""
        service = self.service
        jobs = []
        for _ in range(3):
            jobs.append(self.submit_bell_job(service))

        rjobs = service.jobs(limit=2, program_id="sampler")
        assert len(rjobs) == 2

    def test_retrieve_pending_jobs(self):
        """Test retrieving pending jobs (QUEUED, RUNNING)."""
        service = self.service
        job = self.submit_bell_job(service)
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

    def test_retrieve_returned_jobs(self):
        """Test retrieving returned jobs (COMPLETED, FAILED, CANCELLED)."""
        service = self.service
        job = self.submit_bell_job(service)
        job.wait_for_final_state()
        rjobs = service.jobs(pending=False)
        found = False
        for rjob in rjobs:
            if rjob.job_id() == job.job_id():
                assert job.primitive_id == rjob.primitive_id
                found = True
                break
        assert found

    def test_retrieve_jobs_by_program_id(self):
        """Test retrieving jobs by Program ID."""
        service = self.service
        program_id = "sampler"
        jobs = service.jobs(program_id=program_id)
        for job in jobs:
            assert program_id == job.primitive_id

    def test_retrieve_jobs_by_job_tags(self):
        """Test retrieving jobs by job_tags."""
        service = self.service
        job_tags = ["job_tag_test"]
        job = self.submit_bell_job(service, job_tags=job_tags)
        job.wait_for_final_state()
        rjobs = service.jobs(job_tags=job_tags)
        assert job.job_id() in [j.job_id() for j in rjobs]
        rjobs = service.jobs(job_tags=["no_test_tag"])
        assert not rjobs

    def test_retrieve_jobs_by_instance(self):
        """Test retrieving jobs by instance."""
        service = self.service
        instance = self.dependencies.instance
        rjobs = service.jobs(instance=instance)
        for job in rjobs:
            assert instance == job.instance

    def test_jobs_filter_by_date(self):
        """Test retrieving jobs by creation date."""
        service = self.service
        current_time = datetime.now(timezone.utc) - timedelta(minutes=1)
        job = self.submit_bell_job(service)
        job.wait_for_final_state()
        time_after_job = datetime.now(timezone.utc) + timedelta(minutes=1)
        rjobs = service.jobs(
            created_before=time_after_job, created_after=current_time, pending=False, limit=20
        )
        assert job.job_id() in [j.job_id() for j in rjobs]
        for job in rjobs:
            assert job.creation_date <= time_after_job
            assert job.creation_date >= current_time

    def test_retrieve_jobs_sorted_by_date(self):
        """Test retrieving jobs sorted by the date."""
        service = self.service
        job = self.submit_bell_job(service)
        job.wait_for_final_state()
        job_2 = self.submit_bell_job(service)
        job_2.wait_for_final_state()
        rjobs = service.jobs()
        rjobs_desc = service.jobs(descending=True)

        # The two jobs just submitted are returned newest first
        assert rjobs[0].job_id() == job_2.job_id()
        assert rjobs[1].job_id() == job.job_id()
        assert [job.job_id() for job in rjobs] == [job.job_id() for job in rjobs_desc]

    def test_retrieve_jobs_backend(self):
        """Test retrieving jobs with backend filter."""
        service = self.service
        backend_name = self.test_backend.name
        jobs = service.jobs(backend_name=backend_name)
        for job in jobs:
            assert backend_name == job.backend().name

    def test_retrieve_jobs_include_mocks(self):
        """`service.jobs()` should respect the `include_mocks` flag."""
        service = self.service
        # Skip the test if there are no mock backends.
        _, mock_backend = get_mock_backend_pair(service)

        # Submit job against the mock device.
        job = self.submit_bell_job(service, backend_name=mock_backend.name)
        jobs_no_mocks = service.jobs(limit=1)
        jobs_include_mocks = service.jobs(limit=1, include_mocks=True)

        assert jobs_include_mocks[0].job_id() == job.job_id()
        assert jobs_no_mocks[0].job_id() != job.job_id()
