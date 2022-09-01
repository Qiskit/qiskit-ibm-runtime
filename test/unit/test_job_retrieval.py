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

"""Tests for runtime job retrieval."""

from datetime import datetime, timedelta, timezone
from qiskit_ibm_runtime.exceptions import IBMInputValueError
from .mock.fake_runtime_service import FakeRuntimeService
from ..ibm_test_case import IBMTestCase
from ..decorators import run_quantum_and_cloud_fake
from ..program import run_program, upload_program
from ..utils import mock_wait_for_final_state


class TestRetrieveJobs(IBMTestCase):
    """Class for testing job retrieval."""

    def setUp(self):
        """Initial test setup."""
        super().setUp()
        self._ibm_quantum_service = FakeRuntimeService(
            channel="ibm_quantum", token="my_token"
        )

    @run_quantum_and_cloud_fake
    def test_retrieve_job(self, service):
        """Test retrieving a job."""
        program_id = upload_program(service)
        params = {"param1": "foo"}
        job = run_program(service=service, program_id=program_id, inputs=params)
        rjob = service.job(job.job_id())
        self.assertEqual(job.job_id(), rjob.job_id())
        self.assertEqual(program_id, rjob.program_id)

    @run_quantum_and_cloud_fake
    def test_jobs_no_limit(self, service):
        """Test retrieving jobs without limit."""
        program_id = upload_program(service)

        jobs = []
        for _ in range(25):
            jobs.append(run_program(service, program_id))
        rjobs = service.jobs(limit=None)
        self.assertEqual(25, len(rjobs))

    @run_quantum_and_cloud_fake
    def test_jobs_limit(self, service):
        """Test retrieving jobs with limit."""
        program_id = upload_program(service)

        jobs = []
        job_count = 25
        for _ in range(job_count):
            jobs.append(run_program(service, program_id))

        limits = [21, 30]
        for limit in limits:
            with self.subTest(limit=limit):
                rjobs = service.jobs(limit=limit)
                self.assertEqual(min(limit, job_count), len(rjobs))

    @run_quantum_and_cloud_fake
    def test_jobs_skip(self, service):
        """Test retrieving jobs with skip."""
        program_id = upload_program(service)

        jobs = []
        for _ in range(5):
            jobs.append(run_program(service, program_id))
        rjobs = service.jobs(skip=4)
        self.assertEqual(1, len(rjobs))

    def test_jobs_skip_limit(self):
        """Test retrieving jobs with skip and limit."""
        service = self._ibm_quantum_service
        program_id = upload_program(service)

        jobs = []
        for _ in range(10):
            jobs.append(run_program(service, program_id))
        rjobs = service.jobs(skip=4, limit=2)
        self.assertEqual(2, len(rjobs))

    @run_quantum_and_cloud_fake
    def test_jobs_pending(self, service):
        """Test retrieving pending jobs (QUEUED, RUNNING)."""
        program_id = upload_program(service)

        _, pending_jobs_count, _ = self._populate_jobs_with_all_statuses(
            service, program_id=program_id
        )
        rjobs = service.jobs(pending=True)
        self.assertEqual(pending_jobs_count, len(rjobs))

    def test_jobs_limit_pending(self):
        """Test retrieving pending jobs (QUEUED, RUNNING) with limit."""
        service = self._ibm_quantum_service
        program_id = upload_program(service)

        self._populate_jobs_with_all_statuses(service, program_id=program_id)
        limit = 4
        rjobs = service.jobs(limit=limit, pending=True)
        self.assertEqual(limit, len(rjobs))

    def test_jobs_skip_pending(self):
        """Test retrieving pending jobs (QUEUED, RUNNING) with skip."""
        service = self._ibm_quantum_service
        program_id = upload_program(service)

        _, pending_jobs_count, _ = self._populate_jobs_with_all_statuses(
            service, program_id=program_id
        )
        skip = 4
        rjobs = service.jobs(skip=skip, pending=True)
        self.assertEqual(pending_jobs_count - skip, len(rjobs))

    def test_jobs_limit_skip_pending(self):
        """Test retrieving pending jobs (QUEUED, RUNNING) with limit and skip."""
        service = self._ibm_quantum_service
        program_id = upload_program(service)

        self._populate_jobs_with_all_statuses(service, program_id=program_id)
        limit = 2
        skip = 3
        rjobs = service.jobs(limit=limit, skip=skip, pending=True)
        self.assertEqual(limit, len(rjobs))

    def test_jobs_returned(self):
        """Test retrieving returned jobs (COMPLETED, FAILED, CANCELLED)."""
        service = self._ibm_quantum_service
        program_id = upload_program(service)

        _, _, returned_jobs_count = self._populate_jobs_with_all_statuses(
            service, program_id=program_id
        )
        rjobs = service.jobs(pending=False)
        self.assertEqual(returned_jobs_count, len(rjobs))

    def test_jobs_limit_returned(self):
        """Test retrieving returned jobs (COMPLETED, FAILED, CANCELLED) with limit."""
        service = self._ibm_quantum_service
        program_id = upload_program(service)

        self._populate_jobs_with_all_statuses(service, program_id=program_id)
        limit = 6
        rjobs = service.jobs(limit=limit, pending=False)
        self.assertEqual(limit, len(rjobs))

    def test_jobs_skip_returned(self):
        """Test retrieving returned jobs (COMPLETED, FAILED, CANCELLED) with skip."""
        service = self._ibm_quantum_service
        program_id = upload_program(service)

        _, _, returned_jobs_count = self._populate_jobs_with_all_statuses(
            service, program_id=program_id
        )
        skip = 4
        rjobs = service.jobs(skip=skip, pending=False)
        self.assertEqual(returned_jobs_count - skip, len(rjobs))

    def test_jobs_limit_skip_returned(self):
        """Test retrieving returned jobs (COMPLETED, FAILED, CANCELLED) with limit and skip."""
        service = self._ibm_quantum_service
        program_id = upload_program(service)

        self._populate_jobs_with_all_statuses(service, program_id=program_id)
        limit = 6
        skip = 2
        rjobs = service.jobs(limit=limit, skip=skip, pending=False)
        self.assertEqual(limit, len(rjobs))

    @run_quantum_and_cloud_fake
    def test_jobs_filter_by_program_id(self, service):
        """Test retrieving jobs by Program ID."""
        program_id = upload_program(service)
        program_id_1 = upload_program(service)

        job = run_program(service=service, program_id=program_id)
        job_1 = run_program(service=service, program_id=program_id_1)
        with mock_wait_for_final_state(service, job):
            job.wait_for_final_state()
            job_1.wait_for_final_state()
        rjobs = service.jobs(program_id=program_id)
        self.assertEqual(program_id, rjobs[0].program_id)
        self.assertEqual(1, len(rjobs))

    def test_jobs_filter_by_instance(self):
        """Test retrieving jobs by instance."""
        service = self._ibm_quantum_service
        program_id = upload_program(service)
        instance = FakeRuntimeService.DEFAULT_HGPS[1]

        job = run_program(service=service, program_id=program_id, instance=instance)
        with mock_wait_for_final_state(service, job):
            job.wait_for_final_state()
        rjobs = service.jobs(program_id=program_id, instance=instance)
        self.assertTrue(rjobs)
        self.assertEqual(program_id, rjobs[0].program_id)
        self.assertEqual(1, len(rjobs))
        rjobs = service.jobs(
            program_id=program_id, instance="nohub1/nogroup1/noproject1"
        )
        self.assertFalse(rjobs)

    def test_jobs_filter_by_job_tags(self):
        """Test retrieving jobs by job tags."""
        service = self._ibm_quantum_service
        program_id = upload_program(service)
        job_tags = ["test_tag"]

        job = run_program(service=service, program_id=program_id, job_tags=job_tags)
        with mock_wait_for_final_state(service, job):
            job.wait_for_final_state()
        rjobs = service.jobs(program_id=program_id, job_tags=job_tags)
        self.assertTrue(rjobs)
        self.assertEqual(1, len(rjobs))
        rjobs = service.jobs(program_id=program_id, job_tags=["no_test_tag"])
        self.assertFalse(rjobs)

    def test_jobs_filter_by_session_id(self):
        """Test retrieving jobs by session id."""
        service = self._ibm_quantum_service
        program_id = upload_program(service)

        job = run_program(service=service, program_id=program_id)
        job_2 = run_program(
            service=service, program_id=program_id, session_id=job.job_id()
        )
        with mock_wait_for_final_state(service, job):
            job.wait_for_final_state()
            job_2.wait_for_final_state()
        rjobs = service.jobs(program_id=program_id, session_id=job.job_id())
        self.assertTrue(rjobs)
        self.assertEqual(2, len(rjobs))
        rjobs = service.jobs(program_id=program_id, session_id="no_test_session_id")
        self.assertFalse(rjobs)

    def test_jobs_filter_by_date(self):
        """Test retrieving jobs filtered by date."""
        service = self._ibm_quantum_service
        current_time = datetime.now(timezone.utc) - timedelta(seconds=5)
        job = run_program(service=service)
        with mock_wait_for_final_state(service, job):
            job.wait_for_final_state()
        time_after_job = datetime.now(timezone.utc)
        rjobs = service.jobs(
            created_before=time_after_job,
            created_after=current_time,
        )
        self.assertTrue(job.job_id() in [j.job_id() for j in rjobs])
        self.assertTrue(job._creation_date <= time_after_job)
        self.assertTrue(job._creation_date >= current_time)

    def test_jobs_sort_by_date(self):
        """Test retrieving jobs sorted by the date."""
        service = self._ibm_quantum_service
        program_id = upload_program(service)

        job = run_program(service=service, program_id=program_id)
        job_2 = run_program(service=service, program_id=program_id)
        with mock_wait_for_final_state(service, job):
            job.wait_for_final_state()
            job_2.wait_for_final_state()
        rjobs = service.jobs(program_id=program_id)
        rjobs_desc = service.jobs(program_id=program_id, descending=True)
        rjobs_asc = service.jobs(program_id=program_id, descending=False)
        self.assertTrue(rjobs[0], rjobs_asc[1])
        self.assertTrue(rjobs[1], rjobs_asc[0])
        self.assertEqual(
            [job.job_id() for job in rjobs], [job.job_id() for job in rjobs_desc]
        )

    def test_jobs_bad_instance(self):
        """Test retrieving jobs with bad instance values."""
        service = self._ibm_quantum_service
        with self.assertRaises(IBMInputValueError):
            _ = service.jobs(instance="foo")

    def test_different_hgps(self):
        """Test retrieving job submitted with different hgp."""
        # Initialize with hgp0
        service = FakeRuntimeService(
            channel="ibm_quantum",
            token="some_token",
            instance=FakeRuntimeService.DEFAULT_HGPS[0],
        )
        program_id = upload_program(service)

        # Run with hgp1 backend.
        backend_name = FakeRuntimeService.DEFAULT_UNIQUE_BACKEND_PREFIX + "1"
        job = run_program(service, program_id=program_id, backend_name=backend_name)

        rjob = service.job(job.job_id())
        self.assertIsNotNone(rjob.backend())

    def _populate_jobs_with_all_statuses(self, service, program_id):
        """Populate the database with jobs of all statuses."""
        jobs = []
        pending_jobs_count = 0
        returned_jobs_count = 0
        status_count = {
            "RUNNING": 3,
            "COMPLETED": 4,
            "QUEUED": 2,
            "FAILED": 3,
            "CANCELLED": 2,
        }
        pending_status = ["RUNNING", "QUEUED"]
        for stat, count in status_count.items():
            for _ in range(count):
                jobs.append(
                    run_program(
                        service=service, program_id=program_id, final_status=stat
                    )
                )
                if stat in pending_status:
                    pending_jobs_count += 1
                else:
                    returned_jobs_count += 1
        return jobs, pending_jobs_count, returned_jobs_count
