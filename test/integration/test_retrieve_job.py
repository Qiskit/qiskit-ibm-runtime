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
        rjob = service.job(job.job_id)
        self.assertEqual(job.job_id, rjob.job_id)
        self.assertEqual(self.program_ids[service.auth], rjob.program_id)

    @run_integration_test
    def test_retrieve_job_running(self, service):
        """Test retrieving a running job."""
        job = self._run_program(service, iterations=10)
        wait_for_status(job, JobStatus.RUNNING)
        rjob = service.job(job.job_id)
        self.assertEqual(job.job_id, rjob.job_id)
        self.assertEqual(self.program_ids[service.auth], rjob.program_id)

    @run_integration_test
    def test_retrieve_job_done(self, service):
        """Test retrieving a finished job."""
        job = self._run_program(service)
        job.wait_for_final_state()
        rjob = service.job(job.job_id)
        self.assertEqual(job.job_id, rjob.job_id)
        self.assertEqual(self.program_ids[service.auth], rjob.program_id)

    @run_integration_test
    def test_retrieve_all_jobs(self, service):
        """Test retrieving all jobs."""
        job = self._run_program(service)
        rjobs = service.jobs()
        found = False
        for rjob in rjobs:
            if rjob.job_id == job.job_id:
                self.assertEqual(job.program_id, rjob.program_id)
                self.assertEqual(job.inputs, rjob.inputs)
                found = True
                break
        self.assertTrue(found, f"Job {job.job_id} not returned.")

    @run_integration_test
    def test_retrieve_jobs_limit(self, service):
        """Test retrieving jobs with limit."""
        jobs = []
        for _ in range(3):
            jobs.append(self._run_program(service))

        rjobs = service.jobs(limit=2, program_id=self.program_ids[service.auth])
        self.assertEqual(len(rjobs), 2, f"Retrieved jobs: {[j.job_id for j in rjobs]}")
        job_ids = {job.job_id for job in jobs}
        rjob_ids = {rjob.job_id for rjob in rjobs}
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
            if rjob.job_id == job.job_id:
                self.assertEqual(job.program_id, rjob.program_id)
                self.assertEqual(job.inputs, rjob.inputs)
                found = True
                break

        self.assertTrue(
            found or after_status == JobStatus.RUNNING,
            f"Pending job {job.job_id} not retrieved.",
        )

    @run_integration_test
    def test_retrieve_returned_jobs(self, service):
        """Test retrieving returned jobs (COMPLETED, FAILED, CANCELLED)."""
        job = self._run_program(service)
        job.wait_for_final_state()
        rjobs = service.jobs(pending=False)
        found = False
        for rjob in rjobs:
            if rjob.job_id == job.job_id:
                self.assertEqual(job.program_id, rjob.program_id)
                self.assertEqual(job.inputs, rjob.inputs)
                found = True
                break
        self.assertTrue(found, f"Returned job {job.job_id} not retrieved.")

    @run_integration_test
    def test_retrieve_jobs_by_program_id(self, service):
        """Test retrieving jobs by Program ID."""
        program_id = self._upload_program(service)
        job = self._run_program(service, program_id=program_id)
        job.wait_for_final_state()
        rjobs = service.jobs(program_id=program_id)
        self.assertEqual(program_id, rjobs[0].program_id)
        self.assertEqual(1, len(rjobs), f"Retrieved jobs: {[j.job_id for j in rjobs]}")

    @run_integration_test
    def test_jobs_filter_by_hgp(self, service):
        """Test retrieving jobs by hgp."""
        if self.dependencies.auth == "cloud":
            self.skipTest("Not supported on cloud")

        default_hgp = list(service._hgps.keys())[0]
        program_id = self._upload_program(service)
        job = self._run_program(service, program_id=program_id)
        job.wait_for_final_state()
        rjobs = service.jobs(program_id=program_id, instance=default_hgp)
        self.assertEqual(program_id, rjobs[0].program_id)
        self.assertEqual(1, len(rjobs), f"Retrieved jobs: {[j.job_id for j in rjobs]}")

        uuid_ = uuid.uuid4().hex
        fake_hgp = f"{uuid_}/{uuid_}/{uuid_}"
        rjobs = service.jobs(program_id=program_id, instance=fake_hgp)
        self.assertFalse(rjobs)
