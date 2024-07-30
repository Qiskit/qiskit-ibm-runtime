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
import time
from datetime import datetime, timedelta
from unittest import SkipTest

from dateutil import tz
from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister
from qiskit.compiler import transpile
from qiskit.providers.jobstatus import JobStatus

from qiskit_ibm_runtime import SamplerV2 as Sampler
from qiskit_ibm_runtime.exceptions import RuntimeJobTimeoutError, RuntimeJobNotFound

from ..ibm_test_case import IBMIntegrationTestCase
from ..utils import most_busy_backend, cancel_job_safe, submit_and_cancel, bell


class TestIBMJob(IBMIntegrationTestCase):
    """Test ibm_job module."""

    def setUp(self):
        """Initial test setup."""
        super().setUp()
        self.sim_backend = self.service.backend("ibmq_qasm_simulator")
        self.bell = bell()
        sampler = Sampler(backend=self.sim_backend)
        self.sim_job = sampler.run([self.bell])
        self.last_month = datetime.now() - timedelta(days=30)

    def test_run_multiple_simulator(self):
        """Test running multiple jobs in a simulator."""
        num_qubits = 16
        quantum_register = QuantumRegister(num_qubits, "qr")
        classical_register = ClassicalRegister(num_qubits, "cr")
        quantum_circuit = QuantumCircuit(quantum_register, classical_register)
        for i in range(num_qubits - 1):
            quantum_circuit.cx(quantum_register[i], quantum_register[i + 1])
        quantum_circuit.measure(quantum_register, classical_register)
        num_jobs = 4
        sampler = Sampler(backend=self.sim_backend)
        job_array = [
            sampler.run(transpile([quantum_circuit] * 20), shots=2048) for _ in range(num_jobs)
        ]
        timeout = 30
        start_time = time.time()
        while True:
            check = sum(job.status() == "RUNNING" for job in job_array)
            if check >= 2:
                self.log.info("found %d simultaneous jobs", check)
                break
            if all((job.status() == "DONE" for job in job_array)):
                # done too soon? don't generate error
                self.log.warning("all jobs completed before simultaneous jobs could be detected")
                break
            for job in job_array:
                self.log.info(
                    "%s %s %s %s",
                    job.status(),
                    job.status() == "RUNNING",
                    check,
                    job.job_id(),
                )
            self.log.info("-  %s", str(time.time() - start_time))
            if time.time() - start_time > timeout and self.sim_backend.status().pending_jobs <= 4:
                raise TimeoutError(
                    "Failed to see multiple running jobs after " "{0} seconds.".format(timeout)
                )
            time.sleep(0.2)

        result_array = [job.result() for job in job_array]
        self.log.info("got back all job results")
        # Ensure all jobs have finished.
        self.assertTrue(all((job.status() == "DONE" for job in job_array)))
        self.assertTrue(all((result.metadata for result in result_array)))

        # Ensure job ids are unique.
        job_ids = [job.job_id() for job in job_array]
        self.assertEqual(sorted(job_ids), sorted(list(set(job_ids))))

    def test_cancel(self):
        """Test job cancellation."""
        if self.dependencies.channel == "ibm_cloud":
            raise SkipTest("Cloud account does not have real backend.")
        # Find the most busy backend
        self.service._account.instance = None  # set instance to none to avoid filtering
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
            self.assertTrue(job.status() in ["DONE", "CANCELLED", "ERROR"])

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
                job.status() in ["DONE", "CANCELLED", "ERROR"],
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
        self.assertTrue(job_list)
        for job in job_list:
            self.assertLessEqual(
                job.creation_date,
                past_month_tz_aware,
                "job {} creation date {} not within range".format(job.job_id(), job.creation_date),
            )

    def test_retrieve_jobs_between_datetimes(self):
        """Test retrieving jobs created between two specified datetimes."""
        date_today = datetime.now()
        past_month = date_today - timedelta(30)
        past_two_month = date_today - timedelta(60)

        # Add local tz in order to compare to `creation_date` which is tz aware.
        past_month_tz_aware = past_month.replace(tzinfo=tz.tzlocal())
        past_two_month_tz_aware = past_two_month.replace(tzinfo=tz.tzlocal())

        with self.subTest():
            job_list = self.service.jobs(
                backend_name=self.sim_backend.name,
                limit=2,
                created_after=past_two_month,
                created_before=past_month,
            )
            self.assertTrue(job_list)
            for job in job_list:
                self.assertTrue(
                    (past_two_month_tz_aware <= job.creation_date <= past_month_tz_aware),
                    "job {} creation date {} not within range".format(
                        job.job_id(), job.creation_date
                    ),
                )

    def test_retrieve_jobs_order(self):
        """Test retrieving jobs with different orders."""
        sampler = Sampler(backend=self.sim_backend)
        job = sampler.run([self.bell])
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
        if self.dependencies.channel == "ibm_cloud":
            raise SkipTest("Cloud account does not have real backend.")
        self.service._account.instance = None  # set instance to none to avoid filtering
        backend = most_busy_backend(TestIBMJob.service)
        sampler = Sampler(backend=backend)
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
        self.assertEqual(str(self.bell), str(self.sim_job.inputs["pubs"][0][0]))
