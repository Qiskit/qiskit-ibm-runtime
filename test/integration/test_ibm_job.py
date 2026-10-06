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
import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from dateutil import tz
from qiskit.compiler import transpile
from qiskit.providers.jobstatus import JobStatus
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

from qiskit_ibm_runtime import SamplerV2 as Sampler
from qiskit_ibm_runtime.exceptions import RuntimeJobNotFound, RuntimeJobTimeoutError

from ..utils import bell, cancel_job_safe, most_busy_backend, submit_and_cancel
from .case import IBMIntegrationJobTestCase

if TYPE_CHECKING:
    from qiskit import QuantumCircuit

    from qiskit_ibm_runtime import IBMBackend, RuntimeJobV2

logger = logging.getLogger(__name__)


def run_bell_job(backend: IBMBackend) -> tuple[QuantumCircuit, RuntimeJobV2]:
    """Run a bell circuit for `backend`, returning the circuit and the job."""
    pass_manager = generate_preset_pass_manager(backend=backend, optimization_level=1)
    isa_circuit = pass_manager.run(bell())

    return isa_circuit, Sampler(mode=backend).run([isa_circuit])


def last_month() -> datetime:
    """Return the datetime of a month ago."""
    return datetime.now() - timedelta(days=30)


class TestIBMJob(IBMIntegrationJobTestCase):
    """Test ibm_job module."""

    def test_cancel(self):
        """Test job cancellation."""
        service = self.service
        # Find the most busy backend
        backend = most_busy_backend(service)
        submit_and_cancel(backend, logger)

    def test_retrieve_jobs(self):
        """Test retrieving jobs."""
        backend = self.service.backend(self.dependencies.qpu)
        job_list = self.service.jobs(
            backend_name=backend.name,
            limit=5,
            skip=0,
            created_after=last_month(),
        )
        self.assertLessEqual(len(job_list), 5)
        for job in job_list:
            self.assertTrue(isinstance(job.job_id(), str))

    def test_retrieve_completed_jobs(self):
        """Test retrieving jobs with the completed filter."""
        backend = self.service.backend(self.dependencies.qpu)
        completed_job_list = self.service.jobs(backend_name=backend.name, limit=3, pending=False)
        for job in completed_job_list:
            self.assertTrue(
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

    def test_retrieve_pending_jobs(self):
        """Test retrieving jobs with the pending filter."""
        service = self.service
        yesterday = datetime.now() - timedelta(days=1)
        pending_job_list = service.jobs(
            program_id="sampler",
            limit=3,
            pending=True,
            created_after=last_month(),
            created_before=yesterday,
        )
        for job in pending_job_list:
            self.assertTrue(
                job.status() in ["QUEUED", "RUNNING", JobStatus.QUEUED, JobStatus.RUNNING]
            )

    def test_retrieve_job(self):
        """Test retrieving a single job."""
        backend = self.service.backend(self.dependencies.qpu)
        _, sim_job = run_bell_job(backend)

        retrieved_job = self.service.job(sim_job.job_id())
        self.assertEqual(sim_job.job_id(), retrieved_job.job_id())
        self.assertEqual(sim_job.result().metadata, retrieved_job.result().metadata)

    def test_retrieve_job_error(self):
        """Test retrieving an invalid job."""
        service = self.service
        self.assertRaises(RuntimeJobNotFound, service.job, "BAD_JOB_ID")

    def test_retrieve_jobs_status(self):
        """Test retrieving jobs filtered by status."""
        backend = self.service.backend(self.dependencies.qpu)
        backend_jobs = self.service.jobs(
            backend_name=backend.name,
            limit=5,
            skip=5,
            pending=False,
            created_after=last_month(),
        )
        self.assertTrue(backend_jobs)

        for job in backend_jobs:
            self.assertTrue(
                job.status()
                # Update when RuntimeJob is removed in favor of RuntimeJobV2
                in [
                    "DONE",
                    "CANCELLED",
                    "ERROR",
                    JobStatus.DONE,
                    JobStatus.CANCELLED,
                    JobStatus.ERROR,
                ],
                f"Job {job.job_id()} has status {job.status()} when it should be DONE, CANCELLED, "
                "or ERROR",
            )

    def test_retrieve_jobs_created_after(self):
        """Test retrieving jobs created after a specified datetime."""
        backend = self.service.backend(self.dependencies.qpu)
        past_month = datetime.now() - timedelta(days=30)
        # Add local tz in order to compare to `creation_date` which is tz aware.
        past_month_tz_aware = past_month.replace(tzinfo=tz.tzlocal())

        job_list = self.service.jobs(
            backend_name=backend.name,
            limit=2,
            created_after=past_month,
        )
        self.assertTrue(job_list)
        for job in job_list:
            self.assertGreaterEqual(
                job.creation_date,
                past_month_tz_aware,
                f"job {job.job_id()} creation date {job.creation_date} not within range",
            )

    def test_retrieve_jobs_created_before(self):
        """Test retrieving jobs created before a specified datetime."""
        backend = self.service.backend(self.dependencies.qpu)
        past_month = datetime.now() - timedelta(days=30)
        # Add local tz in order to compare to `creation_date` which is tz aware.
        past_month_tz_aware = past_month.replace(tzinfo=tz.tzlocal())

        job_list = self.service.jobs(
            backend_name=backend.name,
            limit=2,
            created_before=past_month,
        )
        self.assertIsInstance(job_list, list)
        for job in job_list:
            self.assertLessEqual(
                job.creation_date,
                past_month_tz_aware,
                f"job {job.job_id()} creation date {job.creation_date} not within range",
            )

    def test_retrieve_jobs_between_datetime(self):
        """Test retrieving jobs created between two specified datetime."""
        backend = self.service.backend(self.dependencies.qpu)
        date_today = datetime.now()
        past_one_month = date_today - timedelta(30)

        # Add local tz in order to compare to `creation_date` which is tz aware.
        today_tz_aware = date_today.replace(tzinfo=tz.tzlocal())
        past_one_month_tz_aware = past_one_month.replace(tzinfo=tz.tzlocal())

        job_list = self.service.jobs(
            backend_name=backend.name,
            limit=2,
            created_after=past_one_month,
            created_before=date_today,
        )
        self.assertTrue(job_list)
        for job in job_list:
            self.assertTrue(
                (past_one_month_tz_aware <= job.creation_date <= today_tz_aware),
                f"job {job.job_id()} creation date {job.creation_date} not within range",
            )

    def test_retrieve_jobs_order(self):
        """Test retrieving jobs with different orders."""
        backend = self.service.backend(self.dependencies.qpu)
        pass_manager = generate_preset_pass_manager(backend=backend, optimization_level=1)

        job = Sampler(mode=backend).run([pass_manager.run(bell())])
        job.wait_for_final_state()

        newest_jobs = self.service.jobs(
            limit=20,
            pending=False,
            descending=True,
            created_after=last_month(),
        )
        self.assertIn(job.job_id(), [rjob.job_id() for rjob in newest_jobs])

        oldest_jobs = self.service.jobs(
            limit=10,
            pending=False,
            descending=False,
            created_after=last_month(),
        )
        self.assertNotIn(job.job_id(), [rjob.job_id() for rjob in oldest_jobs])

    def test_refresh_job_result(self):
        """Test re-retrieving job result."""
        backend = self.service.backend(self.dependencies.qpu)
        _, sim_job = run_bell_job(backend)
        result = sim_job.result()

        # Save original cached results.
        cached_result = copy.deepcopy(result.metadata)
        self.assertTrue(cached_result)

        # Modify cached results.
        result.metadata["test"] = "modified_result"
        self.assertNotEqual(cached_result, result.metadata)
        self.assertEqual(result.metadata["test"], "modified_result")

        # Re-retrieve result.
        result = sim_job.result()
        self.assertDictEqual(cached_result, result.metadata)
        self.assertFalse("test" in result.metadata)

    def test_wait_for_final_state_timeout(self):
        """Test waiting for job to reach final state times out."""
        backend = most_busy_backend(TestIBMJob.service)
        sampler = Sampler(mode=backend)
        job = sampler.run([transpile(bell(), backend=backend)])
        self.assertRaises(RuntimeJobTimeoutError, job.wait_for_final_state, timeout=0.1)
        cancel_job_safe(job, logger)

    def test_job_circuits(self):
        """Test job circuits."""
        backend = self.service.backend(self.dependencies.qpu)
        circuit, sim_job = run_bell_job(backend)
        self.assertEqual(circuit, sim_job.inputs["pubs"][0][0])
