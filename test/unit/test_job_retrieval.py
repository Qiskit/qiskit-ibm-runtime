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

"""Tests for runtime job retrieval."""

from datetime import datetime, timedelta, timezone

from qiskit_ibm_runtime.qiskit_runtime_service import QiskitRuntimeService

from ..decorators import mock_responses
from ..ibm_test_case import IBMTestCase
from ..program import run_program
from ..registries import Job
from ..utils import mock_wait_for_final_state
from .mock.fake_runtime_service import FakeRuntimeService


class TestRetrieveJobs(IBMTestCase):
    """Class for testing job retrieval."""

    def setUp(self):
        """Initial test setup."""
        super().setUp()
        self._ibm_quantum_service = FakeRuntimeService(
            channel="ibm_quantum_platform", token="my_token"
        )

    @mock_responses
    def test_retrieve_job(self, registry):
        """Test retrieving a job."""
        registry.add_job(Job("1", "common_backend", program="sampler"), "a")

        service = QiskitRuntimeService(token="my_token")
        job = service.job("1")
        self.assertEqual("1", job.job_id())
        self.assertEqual("sampler", job.primitive_id)

    @mock_responses
    def test_jobs_no_limit(self, registry):
        """Test retrieving jobs without limit."""
        for i in range(25):
            registry.add_job(Job(str(i), "common_backend"), "a")

        service = QiskitRuntimeService(token="my_token", instance="a")
        jobs = service.jobs(limit=None)
        self.assertEqual(25, len(jobs))

    @mock_responses
    def test_jobs_limit(self, registry):
        """Test retrieving jobs with limit."""
        for i in range(25):
            registry.add_job(Job(str(i), "common_backend"), "a")

        service = QiskitRuntimeService(token="my_token", instance="a")
        limits = [21, 30]
        for limit in limits:
            with self.subTest(limit=limit):
                jobs = service.jobs(limit=limit)
                self.assertEqual(min(limit, 25), len(jobs))

    @mock_responses
    def test_jobs_skip(self, registry):
        """Test retrieving jobs with skip."""
        for i in range(5):
            registry.add_job(Job(str(i), "common_backend"), "a")

        service = QiskitRuntimeService(token="my_token", instance="a")
        jobs = service.jobs(skip=4)
        self.assertEqual(1, len(jobs))

    @mock_responses
    def test_backend_instance_warnings(self, registry):
        """Test backend instance warnings do not appear."""
        registry.add_job(Job("1", "common_backend", program="sampler"), "a")

        service = QiskitRuntimeService(token="my_token", instance="a")
        with self.assertNoLogs("qiskit_ibm_runtime", level="WARNING"):
            service.jobs()

        with self.assertNoLogs("qiskit_ibm_runtime", level="WARNING"):
            service.job("1")

    @mock_responses
    def test_jobs_skip_limit(self, registry):
        """Test retrieving jobs with skip and limit."""
        for i in range(10):
            registry.add_job(Job(str(i), "common_backend"), "a")

        service = QiskitRuntimeService(token="my_token", instance="a")
        jobs = service.jobs(skip=4, limit=2)
        self.assertEqual(2, len(jobs))

    @mock_responses
    def test_jobs_pending(self, registry):
        """Test retrieving pending jobs (QUEUED, RUNNING)."""
        pending_jobs_count, _ = self.populate_jobs_with_all_statuses(registry)

        service = QiskitRuntimeService(token="my_token", instance="a")
        jobs = service.jobs(pending=True)
        self.assertEqual(pending_jobs_count, len(jobs))

    @mock_responses
    def test_jobs_limit_pending(self, registry):
        """Test retrieving pending jobs (QUEUED, RUNNING) with limit."""
        self.populate_jobs_with_all_statuses(registry)

        service = QiskitRuntimeService(token="my_token", instance="a")
        limit = 4
        jobs = service.jobs(limit=limit, pending=True)
        self.assertEqual(limit, len(jobs))

    @mock_responses
    def test_jobs_skip_pending(self, registry):
        """Test retrieving pending jobs (QUEUED, RUNNING) with skip."""
        pending_jobs_count, _ = self.populate_jobs_with_all_statuses(registry)

        service = QiskitRuntimeService(token="my_token", instance="a")
        skip = 4
        jobs = service.jobs(skip=skip, pending=True)
        self.assertEqual(pending_jobs_count - skip, len(jobs))

    @mock_responses
    def test_jobs_limit_skip_pending(self, registry):
        """Test retrieving pending jobs (QUEUED, RUNNING) with limit and skip."""
        self.populate_jobs_with_all_statuses(registry)

        service = QiskitRuntimeService(token="my_token", instance="a")
        limit = 2
        skip = 3
        jobs = service.jobs(limit=limit, skip=skip, pending=True)
        self.assertEqual(limit, len(jobs))

    @mock_responses
    def test_jobs_returned(self, registry):
        """Test retrieving returned jobs (COMPLETED, FAILED, CANCELLED)."""
        _, returned_jobs_count = self.populate_jobs_with_all_statuses(registry)

        service = QiskitRuntimeService(token="my_token", instance="a")
        jobs = service.jobs(pending=False)
        self.assertEqual(returned_jobs_count, len(jobs))

    @mock_responses
    def test_jobs_limit_returned(self, registry):
        """Test retrieving returned jobs (COMPLETED, FAILED, CANCELLED) with limit."""
        self.populate_jobs_with_all_statuses(registry)

        service = QiskitRuntimeService(token="my_token", instance="a")
        limit = 6
        jobs = service.jobs(limit=limit, pending=False)
        self.assertEqual(limit, len(jobs))

    @mock_responses
    def test_jobs_skip_returned(self, registry):
        """Test retrieving returned jobs (COMPLETED, FAILED, CANCELLED) with skip."""
        _, returned_jobs_count = self.populate_jobs_with_all_statuses(registry)

        service = QiskitRuntimeService(token="my_token", instance="a")
        skip = 4
        jobs = service.jobs(skip=skip, pending=False)
        self.assertEqual(returned_jobs_count - skip, len(jobs))

    @mock_responses
    def test_jobs_limit_skip_returned(self, registry):
        """Test retrieving returned jobs (COMPLETED, FAILED, CANCELLED) with limit and skip."""
        self.populate_jobs_with_all_statuses(registry)

        service = QiskitRuntimeService(token="my_token", instance="a")
        limit = 6
        skip = 2
        jobs = service.jobs(limit=limit, skip=skip, pending=False)
        self.assertEqual(limit, len(jobs))

    def test_jobs_filter_by_job_tags(self):
        """Test retrieving jobs by job tags."""
        service = self._ibm_quantum_service
        program_id = "sampler"
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
        program_id = "sampler"

        job = run_program(service=service, program_id=program_id)
        job_2 = run_program(service=service, program_id=program_id, session_id=job.job_id())
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
        program_id = "sampler"

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
        self.assertEqual([job.job_id() for job in rjobs], [job.job_id() for job in rjobs_desc])

    def test_jobs_bad_instance(self):
        """Test retrieving jobs with bad instance values."""
        service = self._ibm_quantum_service
        with self.assertRaises(Exception):
            _ = service.jobs(instance="foo")

    def test_different_instance(self):
        """Test retrieving job submitted with different instance."""
        # Initialize with first instance
        service = FakeRuntimeService(
            channel="ibm_quantum_platform",
            token="some_token",
            instance=FakeRuntimeService.DEFAULT_CRNS[0],
        )
        program_id = "sampler"

        # Run with different instance
        backend_name = FakeRuntimeService.DEFAULT_UNIQUE_BACKEND_PREFIX + "1"
        job = run_program(service, program_id=program_id, backend_name=backend_name)

        rjob = service.job(job.job_id())
        self.assertIsNotNone(rjob.backend())

    def populate_jobs_with_all_statuses(self, registry, program_id="sampler"):
        """Populate the database with jobs of all statuses."""
        pending_jobs_count = 0
        returned_jobs_count = 0
        status_count = {
            "running": 3,
            "completed": 4,
            "queued": 2,
            "failed": 3,
            "cancelled": 2,
        }

        job_id = 1
        for stat, count in status_count.items():
            for _ in range(count):
                registry.add_job(Job(str(job_id), "common_backend", program_id, stat), "a")
                if stat in ("running", "queued"):
                    pending_jobs_count += 1
                else:
                    returned_jobs_count += 1
                job_id += 1
        return pending_jobs_count, returned_jobs_count

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
                jobs.append(run_program(service=service, program_id=program_id, final_status=stat))
                if stat in pending_status:
                    pending_jobs_count += 1
                else:
                    returned_jobs_count += 1
        return jobs, pending_jobs_count, returned_jobs_count
