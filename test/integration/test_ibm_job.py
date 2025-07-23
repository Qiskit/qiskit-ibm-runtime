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

"""IBMJob Test."""
import copy
from datetime import datetime, timedelta

from dateutil import tz
from qiskit.compiler import transpile
from qiskit.providers.jobstatus import JobStatus
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

from qiskit_ibm_runtime import SamplerV2 as Sampler
from qiskit_ibm_runtime.exceptions import RuntimeJobTimeoutError, RuntimeJobNotFound

from ..ibm_test_case import IBMIntegrationTestCase
from ..utils import most_busy_backend, cancel_job_safe, submit_and_cancel, bell


class TestIBMJob(IBMIntegrationTestCase):
    """Test ibm_job module."""

    def setUp(self):
        """Initial test setup."""
        super().setUp()
        self.sim_backend = self.service.backend(self.dependencies.qpu)
        self.bell = bell()
        sampler = Sampler(mode=self.sim_backend)

        pass_mgr = generate_preset_pass_manager(backend=self.sim_backend, optimization_level=1)
        self.isa_circuit = pass_mgr.run(self.bell)
        self.sim_job = sampler.run([self.isa_circuit])
        self.last_month = datetime.now() - timedelta(days=30)

    def test_cancel(self):
        """Test job cancellation."""
        # Find the most busy backend
        backend = most_busy_backend(self.service)
        submit_and_cancel(backend, self.log)

    def test_retrieve_jobs(self):
        """Test retrieving jobs."""
        job_list = self.service.jobs(
            backend_name=self.sim_backend.name,
            limit=5,
            skip=0,
            created_after=self.last_month,
        )
        self.assertLessEqual(len(job_list), 5)
        for job in job_list:
            self.assertTrue(isinstance(job.job_id(), str))

    def test_retrieve_completed_jobs(self):
        """Test retrieving jobs with the completed filter."""
        completed_job_list = self.service.jobs(
            backend_name=self.sim_backend.name, limit=3, pending=False
        )
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
        yesterday = datetime.now() - timedelta(days=1)
        pending_job_list = self.service.jobs(
            program_id="sampler",
            limit=3,
            pending=True,
            created_after=self.last_month,
            created_before=yesterday,
        )
        for job in pending_job_list:
            self.assertTrue(
                job.status() in ["QUEUED", "RUNNING", JobStatus.QUEUED, JobStatus.RUNNING]
            )

    def test_retrieve_job(self):
        """Test retrieving a single job."""
        retrieved_job = self.service.job(self.sim_job.job_id())
        self.assertEqual(self.sim_job.job_id(), retrieved_job.job_id())
        self.assertEqual(self.sim_job.result().metadata, retrieved_job.result().metadata)

    def test_retrieve_job_error(self):
        """Test retrieving an invalid job."""
        self.assertRaises(RuntimeJobNotFound, self.service.job, "BAD_JOB_ID")

    def test_retrieve_jobs_status(self):
        """Test retrieving jobs filtered by status."""
        backend_jobs = self.service.jobs(
            backend_name=self.sim_backend.name,
            limit=5,
            skip=5,
            pending=False,
            created_after=self.last_month,
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
                "Job {} has status {} when it should be DONE, CANCELLED, or ERROR".format(
                    job.job_id(), job.status()
                ),
            )

    def test_retrieve_jobs_created_after(self):
        """Test retrieving jobs created after a specified datetime."""
        past_month = datetime.now() - timedelta(days=30)
        # Add local tz in order to compare to `creation_date` which is tz aware.
        past_month_tz_aware = past_month.replace(tzinfo=tz.tzlocal())

        job_list = self.service.jobs(
            backend_name=self.sim_backend.name,
            limit=2,
            created_after=past_month,
        )
        self.assertTrue(job_list)
        for job in job_list:
            self.assertGreaterEqual(
                job.creation_date,
                past_month_tz_aware,
                "job {} creation date {} not within range".format(job.job_id(), job.creation_date),
            )

    def test_retrieve_jobs_created_before(self):
        """Test retrieving jobs created before a specified datetime."""
        past_month = datetime.now() - timedelta(days=30)
        # Add local tz in order to compare to `creation_date` which is tz aware.
        past_month_tz_aware = past_month.replace(tzinfo=tz.tzlocal())

        job_list = self.service.jobs(
            backend_name=self.sim_backend.name,
            limit=2,
            created_before=past_month,
        )
        self.assertIsInstance(job_list, list)
        for job in job_list:
            self.assertLessEqual(
                job.creation_date,
                past_month_tz_aware,
                "job {} creation date {} not within range".format(job.job_id(), job.creation_date),
            )

    def test_retrieve_jobs_between_datetime(self):
        """Test retrieving jobs created between two specified datetime."""
        date_today = datetime.now()
        past_one_month = date_today - timedelta(30)

        # Add local tz in order to compare to `creation_date` which is tz aware.
        today_tz_aware = date_today.replace(tzinfo=tz.tzlocal())
        past_one_month_tz_aware = past_one_month.replace(tzinfo=tz.tzlocal())

        with self.subTest():
            job_list = self.service.jobs(
                backend_name=self.sim_backend.name,
                limit=2,
                created_after=past_one_month,
                created_before=date_today,
            )
            self.assertTrue(job_list)
            for job in job_list:
                self.assertTrue(
                    (past_one_month_tz_aware <= job.creation_date <= today_tz_aware),
                    "job {} creation date {} not within range".format(
                        job.job_id(), job.creation_date
                    ),
                )

    def test_retrieve_jobs_order(self):
        """Test retrieving jobs with different orders."""
        sampler = Sampler(mode=self.sim_backend)
        job = sampler.run([self.isa_circuit])
        job.wait_for_final_state()
        newest_jobs = self.service.jobs(
            limit=20,
            pending=False,
            descending=True,
            created_after=self.last_month,
        )
        self.assertIn(job.job_id(), [rjob.job_id() for rjob in newest_jobs])

        oldest_jobs = self.service.jobs(
            limit=10,
            pending=False,
            descending=False,
            created_after=self.last_month,
        )
        self.assertNotIn(job.job_id(), [rjob.job_id() for rjob in oldest_jobs])

    def test_refresh_job_result(self):
        """Test re-retrieving job result."""
        result = self.sim_job.result()

        # Save original cached results.
        cached_result = copy.deepcopy(result.metadata)
        self.assertTrue(cached_result)

        # Modify cached results.
        result.metadata["test"] = "modified_result"
        self.assertNotEqual(cached_result, result.metadata)
        self.assertEqual(result.metadata["test"], "modified_result")

        # Re-retrieve result.
        result = self.sim_job.result()
        self.assertDictEqual(cached_result, result.metadata)
        self.assertFalse("test" in result.metadata)

    def test_wait_for_final_state_timeout(self):
        """Test waiting for job to reach final state times out."""
        backend = most_busy_backend(TestIBMJob.service)
        sampler = Sampler(mode=backend)
        job = sampler.run([transpile(bell(), backend=backend)])
        try:
            self.assertRaises(RuntimeJobTimeoutError, job.wait_for_final_state, timeout=0.1)
        finally:
            # Ensure all threads ended.
            for thread in job._executor._threads:
                thread.join(0.1)
            cancel_job_safe(job, self.log)

    def test_job_circuits(self):
        """Test job circuits."""
        self.assertEqual(self.isa_circuit, self.sim_job.inputs["pubs"][0][0])
