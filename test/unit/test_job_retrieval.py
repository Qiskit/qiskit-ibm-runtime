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

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, cast

import pytest

from qiskit_ibm_runtime.ibm_backend import IBMBackend, IBMRetiredBackend
from qiskit_ibm_runtime.qiskit_runtime_service import QiskitRuntimeService

from ..registries import Backend, Job, OneInstanceNoBackendsRegistry

if TYPE_CHECKING:
    from ..registries.base import BaseRegistry
    from ..registries.entities import JobStatus


def populate_jobs(registry: BaseRegistry) -> tuple[int, int]:
    """Populate the registry with jobs of all statuses."""
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
            registry.add_job(
                Job(f"my_job_{status}_{i}", "common_backend", status=cast("JobStatus", status)), "a"
            )
            if status in pending_status:
                pending_jobs_count += 1
            else:
                returned_jobs_count += 1
    return pending_jobs_count, returned_jobs_count


class TestRetrieveJobs:
    """Class for testing job retrieval."""

    def test_retrieve_job(self, registry: BaseRegistry) -> None:
        """Test retrieving a job."""
        registry.add_job(Job("my_job", "common_backend"), "a")

        service = QiskitRuntimeService(token="my_token")
        job = service.job("my_job")
        assert job.job_id() == "my_job"
        assert job.primitive_id == "sampler"

    def test_jobs_no_limit(self, registry: BaseRegistry) -> None:
        """Test retrieving jobs without limit."""
        for i in range(25):
            registry.add_job(Job(str(i), "common_backend"), "a")

        service = QiskitRuntimeService(token="my_token", instance="a")
        jobs = service.jobs(limit=None)
        assert 25 == len(jobs)

    @pytest.mark.parametrize("limit", [21, 30])
    def test_jobs_limit(self, limit: int, registry: BaseRegistry) -> None:
        """Test retrieving jobs with limit."""
        for i in range(25):
            registry.add_job(Job(str(i), "common_backend"), "a")

        service = QiskitRuntimeService(token="my_token", instance="a")
        jobs = service.jobs(limit=limit)
        assert min(limit, 25) == len(jobs)

    def test_jobs_skip(self, registry: BaseRegistry) -> None:
        """Test retrieving jobs with skip."""
        for i in range(5):
            registry.add_job(Job(str(i), "common_backend"), "a")

        service = QiskitRuntimeService(token="my_token", instance="a")
        jobs = service.jobs(skip=4)
        assert 1 == len(jobs)

    def test_backend_instance_warnings(
        self, registry: BaseRegistry, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test backend instance warnings do not appear."""
        registry.add_job(Job("my_job", "common_backend"), "a")

        service = QiskitRuntimeService(token="my_token", instance="a")
        caplog.clear()
        with caplog.at_level(logging.WARNING, logger="qiskit_ibm_runtime"):
            service.jobs()
        assert not caplog.records

        caplog.clear()
        with caplog.at_level(logging.WARNING, logger="qiskit_ibm_runtime"):
            service.job("my_job")
        assert not caplog.records

    def test_jobs_skip_limit(self, registry: BaseRegistry) -> None:
        """Test retrieving jobs with skip and limit."""
        for i in range(10):
            registry.add_job(Job(str(i), "common_backend"), "a")

        service = QiskitRuntimeService(token="my_token", instance="a")
        jobs = service.jobs(skip=4, limit=2)
        assert 2 == len(jobs)

    def test_jobs_pending(self, registry: BaseRegistry) -> None:
        """Test retrieving pending jobs (QUEUED, RUNNING)."""
        pending_jobs_count, _ = populate_jobs(registry)

        service = QiskitRuntimeService(token="my_token", instance="a")
        jobs = service.jobs(pending=True)
        assert pending_jobs_count == len(jobs)

    def test_jobs_limit_pending(self, registry: BaseRegistry) -> None:
        """Test retrieving pending jobs (QUEUED, RUNNING) with limit."""
        populate_jobs(registry)

        service = QiskitRuntimeService(token="my_token", instance="a")
        limit = 4
        jobs = service.jobs(limit=limit, pending=True)
        assert limit == len(jobs)

    def test_jobs_skip_pending(self, registry: BaseRegistry) -> None:
        """Test retrieving pending jobs (QUEUED, RUNNING) with skip."""
        pending_jobs_count, _ = populate_jobs(registry)

        service = QiskitRuntimeService(token="my_token", instance="a")
        skip = 4
        jobs = service.jobs(skip=skip, pending=True)
        assert pending_jobs_count - skip == len(jobs)

    def test_jobs_limit_skip_pending(self, registry: BaseRegistry) -> None:
        """Test retrieving pending jobs (QUEUED, RUNNING) with limit and skip."""
        populate_jobs(registry)

        service = QiskitRuntimeService(token="my_token", instance="a")
        limit = 2
        skip = 3
        jobs = service.jobs(limit=limit, skip=skip, pending=True)
        assert limit == len(jobs)

    def test_jobs_returned(self, registry: BaseRegistry) -> None:
        """Test retrieving returned jobs (COMPLETED, FAILED, CANCELLED)."""
        _, returned_jobs_count = populate_jobs(registry)

        service = QiskitRuntimeService(token="my_token", instance="a")
        jobs = service.jobs(pending=False)
        assert returned_jobs_count == len(jobs)

    def test_jobs_limit_returned(self, registry: BaseRegistry) -> None:
        """Test retrieving returned jobs (COMPLETED, FAILED, CANCELLED) with limit."""
        populate_jobs(registry)

        service = QiskitRuntimeService(token="my_token", instance="a")
        limit = 6
        jobs = service.jobs(limit=limit, pending=False)
        assert limit == len(jobs)

    def test_jobs_skip_returned(self, registry: BaseRegistry) -> None:
        """Test retrieving returned jobs (COMPLETED, FAILED, CANCELLED) with skip."""
        _, returned_jobs_count = populate_jobs(registry)

        service = QiskitRuntimeService(token="my_token", instance="a")
        skip = 4
        jobs = service.jobs(skip=skip, pending=False)
        assert returned_jobs_count - skip == len(jobs)

    def test_jobs_limit_skip_returned(self, registry: BaseRegistry) -> None:
        """Test retrieving returned jobs (COMPLETED, FAILED, CANCELLED) with limit and skip."""
        populate_jobs(registry)

        service = QiskitRuntimeService(token="my_token", instance="a")
        limit = 4
        skip = 2
        rjobs = service.jobs(limit=limit, skip=skip, pending=False)
        assert limit == len(rjobs)

    def test_jobs_by_instance(self, registry: BaseRegistry) -> None:
        """Test retrieving jobs with bad instance values."""
        registry.add_job(Job("my_job", "common_backend"), "a")
        crn_a = registry.instances["a"].crn
        crn_b = registry.instances["b"].crn

        service = QiskitRuntimeService(token="my_token", instance="a")

        assert len(service.jobs(instance=crn_a)) == 1
        assert len(service.jobs(instance=crn_b)) == 0

    def test_different_instance(self, registry: BaseRegistry) -> None:
        """Test retrieving job submitted with different instance."""
        registry.add_job(Job("my_job", "unique_backend_a"), "a")
        service = QiskitRuntimeService(token="my_token")

        # Ensure the active api client is the one for the instance that does _not_ contain the job.
        assert service._active_api_client._instance == registry.instances["b"].crn

        # Retrieve a job from instance "a" when active instance is "b".
        job = service.job("my_job")
        assert job.backend() is not None

    @pytest.mark.registry(registry_class=OneInstanceNoBackendsRegistry)
    def test_jobs_from_mock_devices(self, registry: OneInstanceNoBackendsRegistry) -> None:
        """Test retrieving jobs from mock devices."""
        registry.add_backend(Backend("ibm_foo"))
        registry.add_backend(Backend("mock_foo", is_mock=True))
        registry.add_job(Job("1", "ibm_foo"), "a")
        registry.add_job(Job("2", "mock_foo"), "a")

        service = QiskitRuntimeService(token="my_token")

        # Jobs from mock devices should be excluded by default.
        jobs = service.jobs()
        assert [job.job_id() for job in jobs] == ["1"]

        # Jobs from mock devices should be included if passing the flag.
        jobs = service.jobs(include_mocks=True)
        assert [job.job_id() for job in jobs] == ["1", "2"]

        # Jobs should be retrieved in all cases.
        job_1 = service.job("1")
        job_2 = service.job("2")
        assert job_1.backend().backend_name == "ibm_foo"
        assert not job_1.backend().is_mock
        assert job_2.backend().backend_name == "mock_foo"
        assert job_2.backend().is_mock

    @pytest.mark.registry(registry_class=OneInstanceNoBackendsRegistry)
    def test_jobs_from_retired_backend(self, registry: OneInstanceNoBackendsRegistry) -> None:
        """Test retrieving jobs that use a retired backend."""
        registry.add_backend(Backend("ibm_not_retired"))
        registry.add_job(Job("1", "ibm_retired"), "a")
        registry.add_job(Job("2", "ibm_not_retired"), "a")

        service = QiskitRuntimeService(token="my_token")

        # Retrieving a job should suceed, and produce a retired backend.
        job_retired = service.job("1")
        assert isinstance(job_retired.backend(), IBMRetiredBackend)

        # Retrieving all (2) jobs should suceed, and produce retired and non retired backends.
        jobs = service.jobs()
        assert isinstance(jobs[0].backend(), IBMRetiredBackend)
        assert isinstance(jobs[1].backend(), IBMBackend)
