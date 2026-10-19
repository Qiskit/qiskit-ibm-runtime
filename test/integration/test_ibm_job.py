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

"""IBMJob Test."""

from __future__ import annotations

import copy
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

import pytest
from dateutil import tz
from qiskit.compiler import transpile
from qiskit.providers.jobstatus import JobStatus
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

from qiskit_ibm_runtime import SamplerV2 as Sampler
from qiskit_ibm_runtime.exceptions import RuntimeJobNotFound, RuntimeJobTimeoutError

from ..utils import bell
from .utils import cancel_job_safe, submit_and_cancel

if TYPE_CHECKING:
    from qiskit import QuantumCircuit

    from qiskit_ibm_runtime import IBMBackend, RuntimeJobV2

    from .dependencies import Dependencies


def run_bell_job(backend: IBMBackend) -> tuple[QuantumCircuit, RuntimeJobV2]:
    """Run a bell circuit for `backend`, returning the circuit and the job."""
    pass_manager = generate_preset_pass_manager(backend=backend, optimization_level=1)
    isa_circuit = pass_manager.run(bell())

    return isa_circuit, Sampler(mode=backend).run([isa_circuit])


def last_month() -> datetime:
    """Return the datetime of a month ago."""
    return datetime.now() - timedelta(days=30)


@pytest.fixture
def most_busy_backend(dependencies: Dependencies) -> IBMBackend:
    """Return the most busy backend available.

    Only backends that have a `pending_jobs` in their `status` are considered. Backends such as
    local backends that do not have this are not considered.
    """
    backends = dependencies.service.backends(simulator=False, operational=True)
    return max(
        (
            b
            for b in backends
            if b.configuration().n_qubits >= 5 and b.status().status_msg == "active"
        ),
        key=lambda b: b.status().pending_jobs,
    )


class TestIBMJob:
    """Test ibm_job module."""

    def test_cancel(self, most_busy_backend: IBMBackend) -> None:
        """Test job cancellation."""
        submit_and_cancel(most_busy_backend)

    def test_retrieve_jobs(self, dependencies: Dependencies) -> None:
        """Test retrieving jobs."""
        service = dependencies.service
        backend = service.backend(dependencies.qpu)
        job_list = service.jobs(
            backend_name=backend.name,
            limit=5,
            skip=0,
            created_after=last_month(),
        )
        assert len(job_list) <= 5
        for job in job_list:
            assert isinstance(job.job_id(), str)

    def test_retrieve_completed_jobs(self, dependencies: Dependencies) -> None:
        """Test retrieving jobs with the completed filter."""
        service = dependencies.service
        backend = service.backend(dependencies.qpu)
        completed_job_list = service.jobs(backend_name=backend.name, limit=3, pending=False)
        for job in completed_job_list:
            assert (
                job.status()
                # Update when RuntimeJob is removed in favor of RuntimeJobV2
                in [
                    "DONE",
                    "CANCELLED",
                    "ERROR",
                    JobStatus.DONE,
                    JobStatus.CANCELLED,
                    JobStatus.ERROR,
                ]
            )

    def test_retrieve_pending_jobs(self, dependencies: Dependencies) -> None:
        """Test retrieving jobs with the pending filter."""
        service = dependencies.service
        yesterday = datetime.now() - timedelta(days=1)
        pending_job_list = service.jobs(
            program_id="sampler",
            limit=3,
            pending=True,
            created_after=last_month(),
            created_before=yesterday,
        )
        for job in pending_job_list:
            assert job.status() in ["QUEUED", "RUNNING", JobStatus.QUEUED, JobStatus.RUNNING]

    def test_retrieve_job(self, dependencies: Dependencies) -> None:
        """Test retrieving a single job."""
        service = dependencies.service
        backend = service.backend(dependencies.qpu)
        _, sim_job = run_bell_job(backend)

        retrieved_job = service.job(sim_job.job_id())
        assert sim_job.job_id() == retrieved_job.job_id()
        assert sim_job.result().metadata == retrieved_job.result().metadata

    def test_retrieve_job_error(self, dependencies: Dependencies) -> None:
        """Test retrieving an invalid job."""
        service = dependencies.service
        with pytest.raises(RuntimeJobNotFound):
            service.job("BAD_JOB_ID")

    def test_retrieve_jobs_status(self, dependencies: Dependencies) -> None:
        """Test retrieving jobs filtered by status."""
        service = dependencies.service
        backend = service.backend(dependencies.qpu)
        backend_jobs = service.jobs(
            backend_name=backend.name,
            limit=5,
            skip=5,
            pending=False,
            created_after=last_month(),
        )
        assert backend_jobs

        for job in backend_jobs:
            assert (
                job.status()
                # Update when RuntimeJob is removed in favor of RuntimeJobV2
                in [
                    "DONE",
                    "CANCELLED",
                    "ERROR",
                    JobStatus.DONE,
                    JobStatus.CANCELLED,
                    JobStatus.ERROR,
                ]
            )

    def test_retrieve_jobs_created_after(self, dependencies: Dependencies) -> None:
        """Test retrieving jobs created after a specified datetime."""
        service = dependencies.service
        backend = service.backend(dependencies.qpu)
        past_month = datetime.now() - timedelta(days=30)
        # Add local tz in order to compare to `creation_date` which is tz aware.
        past_month_tz_aware = past_month.replace(tzinfo=tz.tzlocal())

        job_list = service.jobs(
            backend_name=backend.name,
            limit=2,
            created_after=past_month,
        )
        assert job_list
        for job in job_list:
            assert job.creation_date >= past_month_tz_aware

    def test_retrieve_jobs_created_before(self, dependencies: Dependencies) -> None:
        """Test retrieving jobs created before a specified datetime."""
        service = dependencies.service
        backend = service.backend(dependencies.qpu)
        past_month = datetime.now() - timedelta(days=30)
        # Add local tz in order to compare to `creation_date` which is tz aware.
        past_month_tz_aware = past_month.replace(tzinfo=tz.tzlocal())

        job_list = service.jobs(
            backend_name=backend.name,
            limit=2,
            created_before=past_month,
        )
        assert isinstance(job_list, list)
        for job in job_list:
            assert job.creation_date <= past_month_tz_aware

    def test_retrieve_jobs_between_datetime(self, dependencies: Dependencies) -> None:
        """Test retrieving jobs created between two specified datetime."""
        service = dependencies.service
        backend = service.backend(dependencies.qpu)
        date_today = datetime.now()
        past_one_month = date_today - timedelta(30)

        # Add local tz in order to compare to `creation_date` which is tz aware.
        today_tz_aware = date_today.replace(tzinfo=tz.tzlocal())
        past_one_month_tz_aware = past_one_month.replace(tzinfo=tz.tzlocal())

        job_list = service.jobs(
            backend_name=backend.name,
            limit=2,
            created_after=past_one_month,
            created_before=date_today,
        )
        assert job_list
        for job in job_list:
            assert past_one_month_tz_aware <= job.creation_date <= today_tz_aware

    def test_retrieve_jobs_order(self, dependencies: Dependencies) -> None:
        """Test retrieving jobs with different orders."""
        service = dependencies.service
        backend = service.backend(dependencies.qpu)
        _, job = run_bell_job(backend)
        job.wait_for_final_state()

        newest_jobs = service.jobs(
            limit=20,
            pending=False,
            descending=True,
            created_after=last_month(),
        )
        assert job.job_id() in [rjob.job_id() for rjob in newest_jobs]

        oldest_jobs = service.jobs(
            limit=10,
            pending=False,
            descending=False,
            created_after=last_month(),
        )
        assert job.job_id() not in [rjob.job_id() for rjob in oldest_jobs]

    def test_refresh_job_result(self, dependencies: Dependencies) -> None:
        """Test re-retrieving job result."""
        service = dependencies.service
        backend = service.backend(dependencies.qpu)
        _, sim_job = run_bell_job(backend)
        result = sim_job.result()

        # Save original cached results.
        cached_result = copy.deepcopy(result.metadata)
        assert cached_result

        # Modify cached results.
        result.metadata["test"] = "modified_result"
        assert cached_result != result.metadata
        assert result.metadata["test"] == "modified_result"

        # Re-retrieve result.
        result = sim_job.result()
        assert cached_result == result.metadata
        assert "test" not in result.metadata

    def test_wait_for_final_state_timeout(self, most_busy_backend: IBMBackend) -> None:
        """Test waiting for job to reach final state times out."""
        sampler = Sampler(mode=most_busy_backend)
        job = sampler.run([transpile(bell(), backend=most_busy_backend)])
        with pytest.raises(RuntimeJobTimeoutError):
            job.wait_for_final_state(timeout=0.1)
        cancel_job_safe(job)

    def test_job_circuits(self, dependencies: Dependencies) -> None:
        """Test job circuits."""
        service = dependencies.service
        backend = service.backend(dependencies.qpu)
        circuit, sim_job = run_bell_job(backend)
        assert circuit == sim_job.inputs["pubs"][0][0]
