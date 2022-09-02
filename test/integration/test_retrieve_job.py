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

"""Tests for job functions using real runtime service."""

import uuid
from datetime import datetime, timezone
from qiskit.providers.jobstatus import JobStatus

from ..ibm_test_case import IBMIntegrationJobTestCase
from ..decorators import run_integration_test
from ..utils import wait_for_status, get_real_device


class TestIntegrationRetrieveJob(IBMIntegrationJobTestCase):
    """Integration tests for job retrieval functions."""

    @run_integration_test
    def test_retrieve_job_queued(self, service):
        """Test retrieving a queued job."""
        real_device = get_real_device(service)
        _ = self._run_program(service, iterations=10, backend=real_device)
        job = self._run_program(service, iterations=2, backend=real_device)
        wait_for_status(job, JobStatus.QUEUED)
        rjob = service.job(job.job_id())
        self.assertEqual(job.job_id(), rjob.job_id())
        self.assertEqual(self.program_ids[service.channel], rjob.program_id)

    @run_integration_test
    def test_retrieve_job_running(self, service):
        """Test retrieving a running job."""
        job = self._run_program(service, iterations=10)
        wait_for_status(job, JobStatus.RUNNING)
        rjob = service.job(job.job_id())
        self.assertEqual(job.job_id(), rjob.job_id())
        self.assertEqual(self.program_ids[service.channel], rjob.program_id)

    @run_integration_test
    def test_retrieve_job_done(self, service):
        """Test retrieving a finished job."""
        job = self._run_program(service)
        job.wait_for_final_state()
        rjob = service.job(job.job_id())
        self.assertEqual(job.job_id(), rjob.job_id())
        self.assertEqual(self.program_ids[service.channel], rjob.program_id)

    @run_integration_test
    def test_retrieve_all_jobs(self, service):
        """Test retrieving all jobs."""
        job = self._run_program(service)
        rjobs = service.jobs()
        found = False
        for rjob in rjobs:
            if rjob.job_id() == job.job_id():
                self.assertEqual(job.program_id, rjob.program_id)
                self.assertEqual(job.inputs, rjob.inputs)
                found = True
                break
        self.assertTrue(found, f"Job {job.job_id()} not returned.")

    @run_integration_test
    def test_retrieve_jobs_limit(self, service):
        """Test retrieving jobs with limit."""
        jobs = []
        for _ in range(3):
            jobs.append(self._run_program(service))

        rjobs = service.jobs(limit=2, program_id=self.program_ids[service.channel])
        self.assertEqual(
            len(rjobs), 2, f"Retrieved jobs: {[j.job_id() for j in rjobs]}"
        )
        job_ids = {job.job_id() for job in jobs}
        rjob_ids = {rjob.job_id() for rjob in rjobs}
        self.assertTrue(
            rjob_ids.issubset(job_ids), f"Submitted: {job_ids}, Retrieved: {rjob_ids}"
        )

    @run_integration_test
    def test_retrieve_pending_jobs(self, service):
        """Test retrieving pending jobs (QUEUED, RUNNING)."""
        job = self._run_program(service, iterations=10)
        wait_for_status(job, JobStatus.RUNNING)
        rjobs = service.jobs(pending=True)
        after_status = job.status()
        found = False
        for rjob in rjobs:
            if rjob.job_id() == job.job_id():
                self.assertEqual(job.program_id, rjob.program_id)
                self.assertEqual(job.inputs, rjob.inputs)
                found = True
                break

        self.assertTrue(
            found or after_status == JobStatus.RUNNING,
            f"Pending job {job.job_id()} not retrieved.",
        )

    @run_integration_test
    def test_retrieve_returned_jobs(self, service):
        """Test retrieving returned jobs (COMPLETED, FAILED, CANCELLED)."""
        job = self._run_program(service)
        job.wait_for_final_state()
        rjobs = service.jobs(pending=False)
        found = False
        for rjob in rjobs:
            if rjob.job_id() == job.job_id():
                self.assertEqual(job.program_id, rjob.program_id)
                self.assertEqual(job.inputs, rjob.inputs)
                found = True
                break
        self.assertTrue(found, f"Returned job {job.job_id()} not retrieved.")

    @run_integration_test
    def test_retrieve_jobs_by_program_id(self, service):
        """Test retrieving jobs by Program ID."""
        program_id = self._upload_program(service)
        job = self._run_program(service, program_id=program_id)
        job.wait_for_final_state()
        rjobs = service.jobs(program_id=program_id)
        self.assertEqual(program_id, rjobs[0].program_id)
        self.assertEqual(
            1, len(rjobs), f"Retrieved jobs: {[j.job_id() for j in rjobs]}"
        )

    @run_integration_test
    def test_retrieve_jobs_by_job_tags(self, service):
        """Test retrieving jobs by job_tags."""
        job_tags = ["test_tag"]
        job = self._run_program(service, job_tags=job_tags)
        job.wait_for_final_state()
        rjobs = service.jobs(job_tags=job_tags)
        self.assertEqual(
            1, len(rjobs), f"Retrieved jobs: {[j.job_id() for j in rjobs]}"
        )
        rjobs = service.jobs(job_tags=["no_test_tag"])
        self.assertFalse(rjobs)

    @run_integration_test
    def test_retrieve_jobs_by_session_id(self, service):
        """Test retrieving jobs by session_id."""
        job = self._run_program(service, start_session=True)
        job.wait_for_final_state()
        job_2 = self._run_program(service, session_id=job.job_id())
        job_2.wait_for_final_state()
        rjobs = service.jobs(session_id=job.job_id())
        self.assertEqual(
            2, len(rjobs), f"Retrieved jobs: {[j.job_id() for j in rjobs]}"
        )
        rjobs = service.jobs(session_id="test")
        self.assertFalse(rjobs)

    @run_integration_test
    def test_jobs_filter_by_date(self, service):
        """Test retrieving jobs by creation date."""
        current_time = datetime.now(timezone.utc)
        job = self._run_program(service)
        job.wait_for_final_state()
        time_after_job = datetime.now(timezone.utc)
        rjobs = service.jobs(created_before=time_after_job, created_after=current_time)
        self.assertTrue(job.job_id() in [j.job_id() for j in rjobs])
        for job in rjobs:
            self.assertTrue(job.creation_date <= time_after_job)
            self.assertTrue(job.creation_date >= current_time)

    @run_integration_test
    def test_jobs_filter_by_hgp(self, service):
        """Test retrieving jobs by hgp."""
        if self.dependencies.channel == "ibm_cloud":
            self.skipTest("Not supported on ibm_cloud")

        default_hgp = list(service._hgps.keys())[0]
        program_id = self._upload_program(service)
        job = self._run_program(service, program_id=program_id)
        job.wait_for_final_state()
        rjobs = service.jobs(program_id=program_id, instance=default_hgp)
        self.assertEqual(program_id, rjobs[0].program_id)
        self.assertEqual(
            1, len(rjobs), f"Retrieved jobs: {[j.job_id() for j in rjobs]}"
        )

        uuid_ = uuid.uuid4().hex
        fake_hgp = f"{uuid_}/{uuid_}/{uuid_}"
        rjobs = service.jobs(program_id=program_id, instance=fake_hgp)
        self.assertFalse(rjobs)

    @run_integration_test
    def test_retrieve_jobs_sorted_by_date(self, service):
        """Test retrieving jobs sorted by the date."""
        job = self._run_program(service)
        job.wait_for_final_state()
        job_2 = self._run_program(service)
        job_2.wait_for_final_state()
        rjobs = service.jobs()
        rjobs_desc = service.jobs(descending=True)
        rjobs_asc = service.jobs(descending=False)
        self.assertTrue(rjobs[0], rjobs_asc[1])
        self.assertTrue(rjobs[1], rjobs_asc[0])
        self.assertEqual(
            [job.job_id() for job in rjobs], [job.job_id() for job in rjobs_desc]
        )
