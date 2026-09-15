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

from ddt import data, ddt

from qiskit_ibm_runtime.ibm_backend import IBMBackend, IBMRetiredBackend
from qiskit_ibm_runtime.qiskit_runtime_service import QiskitRuntimeService

from ..decorators import mock_responses
from ..ibm_test_case import IBMTestCase
from ..registries import Backend, Job, OneInstanceNoBackendsRegistry


@ddt
class TestRetrieveJobs(IBMTestCase):
    """Class for testing job retrieval."""

    @mock_responses
    def test_retrieve_job(self, registry):
        """Test retrieving a job."""
        registry.add_job(Job("my_job", "common_backend"), "a")

        service = QiskitRuntimeService(token="my_token")
        job = service.job("my_job")
        self.assertEqual(job.job_id(), "my_job")
        self.assertEqual(job.primitive_id, "sampler")

    @mock_responses
    def test_jobs_no_limit(self, registry):
        """Test retrieving jobs without limit."""
        for i in range(25):
            registry.add_job(Job(str(i), "common_backend"), "a")

        service = QiskitRuntimeService(token="my_token", instance="a")
        jobs = service.jobs(limit=None)
        self.assertEqual(25, len(jobs))

    @data(21, 30)
    @mock_responses
    def test_jobs_limit(self, limit, registry):
        """Test retrieving jobs with limit."""
        for i in range(25):
            registry.add_job(Job(str(i), "common_backend"), "a")

        service = QiskitRuntimeService(token="my_token", instance="a")
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
        registry.add_job(Job("my_job", "common_backend"), "a")

        service = QiskitRuntimeService(token="my_token", instance="a")
        with self.assertNoLogs("qiskit_ibm_runtime", level="WARNING"):
            service.jobs()

        with self.assertNoLogs("qiskit_ibm_runtime", level="WARNING"):
            service.job("my_job")

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
        _, pending_jobs_count, _ = self._populate_jobs(registry)

        service = QiskitRuntimeService(token="my_token", instance="a")
        jobs = service.jobs(pending=True)
        self.assertEqual(pending_jobs_count, len(jobs))

    @mock_responses
    def test_jobs_limit_pending(self, registry):
        """Test retrieving pending jobs (QUEUED, RUNNING) with limit."""
        self._populate_jobs(registry)

        service = QiskitRuntimeService(token="my_token", instance="a")
        limit = 4
        jobs = service.jobs(limit=limit, pending=True)
        self.assertEqual(limit, len(jobs))

    @mock_responses
    def test_jobs_skip_pending(self, registry):
        """Test retrieving pending jobs (QUEUED, RUNNING) with skip."""
        _, pending_jobs_count, _ = self._populate_jobs(registry)

        service = QiskitRuntimeService(token="my_token", instance="a")
        skip = 4
        jobs = service.jobs(skip=skip, pending=True)
        self.assertEqual(pending_jobs_count - skip, len(jobs))

    @mock_responses
    def test_jobs_limit_skip_pending(self, registry):
        """Test retrieving pending jobs (QUEUED, RUNNING) with limit and skip."""
        self._populate_jobs(registry)

        service = QiskitRuntimeService(token="my_token", instance="a")
        limit = 2
        skip = 3
        jobs = service.jobs(limit=limit, skip=skip, pending=True)
        self.assertEqual(limit, len(jobs))

    @mock_responses
    def test_jobs_returned(self, registry):
        """Test retrieving returned jobs (COMPLETED, FAILED, CANCELLED)."""
        _, _, returned_jobs_count = self._populate_jobs(registry)

        service = QiskitRuntimeService(token="my_token", instance="a")
        jobs = service.jobs(pending=False)
        self.assertEqual(returned_jobs_count, len(jobs))

    @mock_responses
    def test_jobs_limit_returned(self, registry):
        """Test retrieving returned jobs (COMPLETED, FAILED, CANCELLED) with limit."""
        self._populate_jobs(registry)

        service = QiskitRuntimeService(token="my_token", instance="a")
        limit = 6
        jobs = service.jobs(limit=limit, pending=False)
        self.assertEqual(limit, len(jobs))

    @mock_responses
    def test_jobs_skip_returned(self, registry):
        """Test retrieving returned jobs (COMPLETED, FAILED, CANCELLED) with skip."""
        _, _, returned_jobs_count = self._populate_jobs(registry)

        service = QiskitRuntimeService(token="my_token", instance="a")
        skip = 4
        jobs = service.jobs(skip=skip, pending=False)
        self.assertEqual(returned_jobs_count - skip, len(jobs))

    @mock_responses
    def test_jobs_limit_skip_returned(self, registry):
        """Test retrieving returned jobs (COMPLETED, FAILED, CANCELLED) with limit and skip."""
        self._populate_jobs(registry)

        service = QiskitRuntimeService(token="my_token", instance="a")
        limit = 4
        skip = 2
        rjobs = service.jobs(limit=limit, skip=skip, pending=False)
        self.assertEqual(limit, len(rjobs))

    @mock_responses
    def test_jobs_by_instance(self, registry):
        """Test retrieving jobs with bad instance values."""
        registry.add_job(Job("my_job", "common_backend"), "a")
        crn_a = registry.instances["a"].crn
        crn_b = registry.instances["b"].crn

        service = QiskitRuntimeService(token="my_token", instance="a")

        self.assertEqual(len(service.jobs(instance=crn_a)), 1)
        self.assertEqual(len(service.jobs(instance=crn_b)), 0)

    @mock_responses
    def test_different_instance(self, registry):
        """Test retrieving job submitted with different instance."""
        registry.add_job(Job("my_job", "unique_backend_a"), "a")
        service = QiskitRuntimeService(token="my_token")

        # Ensure the active api client is the one for the instance that does _not_ contain the job.
        self.assertEqual(service._active_api_client._instance, registry.instances["b"].crn)

        # Retrieve a job from instance "a" when active instance is "b".
        job = service.job("my_job")
        self.assertIsNotNone(job.backend())

    def _populate_jobs(self, registry):
        """Populate the registry with jobs of all statuses."""
        jobs = []
        pending_jobs_count = 0
        returned_jobs_count = 0
        status_count = {
            "queued": 3,
            "running": 4,
            "completed": 2,
            "failed": 3,
            "cancelled": 2,
        }

        pending_status = ["running", "queued"]
        for status, count in status_count.items():
            for i in range(count):
                registry.add_job(Job(f"my_job_{status}_{i}", "common_backend", status=status), "a")
                if status in pending_status:
                    pending_jobs_count += 1
                else:
                    returned_jobs_count += 1
        return jobs, pending_jobs_count, returned_jobs_count


class TestRetrieveJobsRegistry(IBMTestCase):
    """Test retrieval of jobs, using a mocked registry."""

    @mock_responses(OneInstanceNoBackendsRegistry)
    def test_jobs_returned_from_retired_backend(
        self, registry: OneInstanceNoBackendsRegistry
    ) -> None:
        """Test retrieving jobs that use a retired backend."""
        registry.add_backend(Backend("ibm_not_retired"))
        registry.add_job(Job("1", "ibm_retired"), "a")
        registry.add_job(Job("2", "ibm_not_retired"), "a")

        service = QiskitRuntimeService(token="my_token")

        # Retrieving a job should suceed, and produce a retired backend.
        job_retired = service.job("1")
        self.assertIsInstance(job_retired.backend(), IBMRetiredBackend)

        # Retrieving all (2) jobs should suceed, and produce retired and non retired backends.
        jobs = service.jobs()
        self.assertIsInstance(jobs[0].backend(), IBMRetiredBackend)
        self.assertIsInstance(jobs[1].backend(), IBMBackend)
