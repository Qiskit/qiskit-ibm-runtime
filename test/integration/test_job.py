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

import random
import time

from qiskit.providers.jobstatus import JOB_FINAL_STATES, JobStatus
from qiskit.test.decorators import slow_test

from qiskit_ibm_runtime.constants import API_TO_JOB_ERROR_MESSAGE
from qiskit_ibm_runtime.exceptions import (
    IBMRuntimeError,
    RuntimeJobFailureError,
    RuntimeInvalidStateError,
    RuntimeJobNotFound,
    RuntimeJobMaxTimeoutError,
)
from ..ibm_test_case import IBMIntegrationJobTestCase
from ..decorators import run_integration_test, production_only
from ..serialization import (
    get_complex_types,
    SerializableClassDecoder,
    SerializableClass,
)
from ..utils import cancel_job_safe, wait_for_status, get_real_device


class TestIntegrationJob(IBMIntegrationJobTestCase):
    """Integration tests for job functions."""

    @run_integration_test
    def test_run_program(self, service):
        """Test running a program."""
        job = self._run_program(service, final_result="foo")
        result = job.result()
        self.assertEqual(JobStatus.DONE, job.status())
        self.assertEqual("foo", result)

    @slow_test
    @run_integration_test
    def test_run_program_real_device(self, service):
        """Test running a program."""
        device = get_real_device(service)
        job = self._run_program(service, final_result="foo", backend=device)
        result = job.result()
        self.assertEqual(JobStatus.DONE, job.status())
        self.assertEqual("foo", result)

    @run_integration_test
    def test_run_program_cloud_no_backend(self, service):
        """Test running a cloud program with no backend."""

        if self.dependencies.channel == "ibm_quantum":
            self.skipTest("Not supported on ibm_quantum")

        job = self._run_program(service, backend="")
        self.assertTrue(job.backend(), f"Job {job.job_id()} has no backend.")

    @run_integration_test
    def test_run_program_log_level(self, service):
        """Test running with a custom log level."""
        levels = ["INFO", "ERROR"]
        for level in levels:
            with self.subTest(level=level):
                job = self._run_program(service, log_level=level)
                job.wait_for_final_state()
                expect_info_msg = level == "INFO"
                self.assertEqual(
                    "info log" in job.logs(),
                    expect_info_msg,
                    f"Job log is {job.logs()}",
                )

    @run_integration_test
    def test_run_program_failed(self, service):
        """Test a failed program execution."""
        job = self._run_program(service, inputs={})
        job.wait_for_final_state()
        self.assertEqual(JobStatus.ERROR, job.status())
        self.assertIn(
            API_TO_JOB_ERROR_MESSAGE["FAILED"].format(job.job_id(), ""),
            job.error_message(),
        )
        with self.assertRaises(RuntimeJobFailureError):
            job.result()
        # TODO: Re-enable when ntc-1651 is fixed
        # self.assertIn("KeyError", str(err_cm.exception))

    @run_integration_test
    def test_run_program_failed_ran_too_long(self, service):
        """Test a program that failed since it ran longer than maximum execution time."""
        max_execution_time = 60
        inputs = {"iterations": 1, "sleep_per_iteration": 61}
        program_id = self._upload_program(
            service, max_execution_time=max_execution_time
        )
        job = self._run_program(service, program_id=program_id, inputs=inputs)

        job.wait_for_final_state()
        job_result_raw = service._api_client.job_results(job.job_id())
        self.assertEqual(JobStatus.ERROR, job.status())
        self.assertIn(
            API_TO_JOB_ERROR_MESSAGE["CANCELLED - RAN TOO LONG"].format(
                job.job_id(), job_result_raw
            ),
            job.error_message(),
        )
        with self.assertRaises(RuntimeJobMaxTimeoutError):
            job.result()

    @run_integration_test
    def test_run_program_override_max_execution_time(self, service):
        """Test that the program max execution time is overridden."""
        program_max_execution_time = 400
        job_max_execution_time = 350
        program_id = self._upload_program(
            service, max_execution_time=program_max_execution_time
        )
        job = self._run_program(
            service, program_id=program_id, max_execution_time=job_max_execution_time
        )
        job.wait_for_final_state()
        self.assertEqual(
            job._api_client.job_get(job.job_id())["cost"], job_max_execution_time
        )

    @run_integration_test
    def test_invalid_max_execution_time_fails(self, service):
        """Test that program fails when max_execution_time is less than 300."""
        with self.assertRaises(IBMRuntimeError):
            self._run_program(service, max_execution_time=299)

    @run_integration_test
    @production_only
    def test_cancel_job_queued(self, service):
        """Test canceling a queued job."""
        real_device = get_real_device(service)
        _ = self._run_program(service, iterations=10, backend=real_device)
        job = self._run_program(service, iterations=2, backend=real_device)
        wait_for_status(job, JobStatus.QUEUED)
        if not cancel_job_safe(job, self.log):
            return
        time.sleep(10)  # Wait a bit for DB to update.
        rjob = service.job(job.job_id())
        self.assertEqual(rjob.status(), JobStatus.CANCELLED)

    @run_integration_test
    def test_cancel_job_running(self, service):
        """Test canceling a running job."""
        job = self._run_program(service, iterations=3)
        wait_for_status(job, JobStatus.RUNNING)
        if not cancel_job_safe(job, self.log):
            return
        time.sleep(10)  # Wait a bit for DB to update.
        rjob = service.job(job.job_id())
        self.assertEqual(rjob.status(), JobStatus.CANCELLED)

    @run_integration_test
    def test_cancel_job_done(self, service):
        """Test canceling a finished job."""
        job = self._run_program(service)
        job.wait_for_final_state()
        with self.assertRaises(RuntimeInvalidStateError):
            job.cancel()

    @run_integration_test
    def test_delete_job(self, service):
        """Test deleting a job."""
        sub_tests = [JobStatus.RUNNING, JobStatus.DONE]
        for status in sub_tests:
            with self.subTest(status=status):
                job = self._run_program(service, iterations=2)
                wait_for_status(job, status)
                service.delete_job(job.job_id())
                with self.assertRaises(RuntimeJobNotFound):
                    service.job(job.job_id())

    @run_integration_test
    @production_only
    def test_delete_job_queued(self, service):
        """Test deleting a queued job."""
        real_device = get_real_device(service)
        _ = self._run_program(service, iterations=10, backend=real_device)
        job = self._run_program(service, iterations=2, backend=real_device)
        wait_for_status(job, JobStatus.QUEUED)
        service.delete_job(job.job_id())
        with self.assertRaises(RuntimeJobNotFound):
            service.job(job.job_id())

    @run_integration_test
    def test_final_result(self, service):
        """Test getting final result."""
        final_result = get_complex_types()
        job = self._run_program(service, final_result=final_result)
        result = job.result(decoder=SerializableClassDecoder)
        self.assertEqual(final_result, result)

        rresults = service.job(job.job_id()).result(decoder=SerializableClassDecoder)
        self.assertEqual(final_result, rresults)

    @run_integration_test
    def test_job_status(self, service):
        """Test job status."""
        job = self._run_program(service, iterations=1)
        time.sleep(random.randint(1, 5))
        self.assertTrue(job.status())

    @run_integration_test
    def test_job_inputs(self, service):
        """Test job inputs."""
        interim_results = get_complex_types()
        inputs = {"iterations": 1, "interim_results": interim_results}
        job = self._run_program(service, inputs=inputs)
        self.assertEqual(inputs, job.inputs)
        rjob = service.job(job.job_id())
        rinterim_results = rjob.inputs["interim_results"]
        self._assert_complex_types_equal(interim_results, rinterim_results)

    @run_integration_test
    def test_job_backend(self, service):
        """Test job backend."""
        job = self._run_program(service)
        self.assertEqual(self.sim_backends[service.channel], job.backend().name)

    @run_integration_test
    def test_job_program_id(self, service):
        """Test job program ID."""
        job = self._run_program(service)
        self.assertEqual(self.program_ids[service.channel], job.program_id)

    @run_integration_test
    def test_wait_for_final_state(self, service):
        """Test wait for final state."""
        job = self._run_program(service)
        job.wait_for_final_state()
        self.assertEqual(JobStatus.DONE, job.status())

    @run_integration_test
    def test_wait_for_final_state_after_job_status(self, service):
        """Test wait for final state on a completed job when the status is updated first."""
        job = self._run_program(service)
        status = job.status()
        while status not in JOB_FINAL_STATES:
            status = job.status()
        job.wait_for_final_state()
        self.assertEqual(JobStatus.DONE, job.status())

    @run_integration_test
    def test_job_creation_date(self, service):
        """Test job creation date."""
        job = self._run_program(service, iterations=1)
        self.assertTrue(job.creation_date)
        rjob = service.job(job.job_id())
        self.assertTrue(rjob.creation_date)
        rjobs = service.jobs(limit=2)
        for rjob in rjobs:
            self.assertTrue(rjob.creation_date)

    @run_integration_test
    def test_job_logs(self, service):
        """Test job logs."""
        job = self._run_program(service, final_result="foo")
        with self.assertLogs("qiskit_ibm_runtime", "WARN"):
            job.logs()
        job.wait_for_final_state()
        job_logs = job.logs()
        self.assertIn("this is a stdout message", job_logs)
        self.assertIn("this is a stderr message", job_logs)

    @run_integration_test
    def test_job_metrics(self, service):
        """Test job metrics."""
        job = self._run_program(service)
        job.wait_for_final_state()
        metrics = job.metrics()
        self.assertTrue(metrics)
        self.assertIn("timestamps", metrics)
        self.assertIn("qiskit_version", metrics)

    def _assert_complex_types_equal(self, expected, received):
        """Verify the received data in complex types is expected."""
        if "serializable_class" in received:
            received["serializable_class"] = SerializableClass.from_json(
                received["serializable_class"]
            )
        self.assertEqual(expected, received)
