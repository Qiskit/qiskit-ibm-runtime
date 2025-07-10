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

"""Tests for job related runtime functions."""

import random
import time

from qiskit.providers.exceptions import QiskitBackendNotFoundError

from qiskit_ibm_runtime import RuntimeJobV2
from qiskit_ibm_runtime.constants import API_TO_JOB_ERROR_MESSAGE
from qiskit_ibm_runtime.exceptions import (
    RuntimeJobFailureError,
    RuntimeJobNotFound,
    RuntimeJobMaxTimeoutError,
    RuntimeInvalidStateError,
)
from .mock.fake_runtime_client import (
    FailedRuntimeJob,
    FailedRanTooLongRuntimeJob,
    CancelableRuntimeJob,
)
from ..ibm_test_case import IBMTestCase
from ..decorators import run_cloud_fake
from ..program import run_program
from ..utils import mock_wait_for_final_state


class TestRuntimeJob(IBMTestCase):
    """Class for testing runtime jobs."""

    @run_cloud_fake
    def test_run_program(self, service):
        """Test running program."""
        params = {"param1": "foo"}
        job = run_program(service=service, inputs=params)
        self.assertTrue(job.job_id())
        self.assertIsInstance(job, RuntimeJobV2)
        with mock_wait_for_final_state(service, job):
            job.wait_for_final_state()
            self.assertEqual(job.status(), "DONE")
            self.assertTrue(job.result())

    @run_cloud_fake
    def test_run_program_phantom_backend(self, service):
        """Test running on a phantom backend."""
        with self.assertRaises(QiskitBackendNotFoundError):
            _ = run_program(service=service, backend_name="phantom_backend")

    @run_cloud_fake
    def test_run_program_with_custom_runtime_image(self, service):
        """Test running program with a custom image."""
        params = {"param1": "foo"}
        image = "name:tag"
        job = run_program(service=service, inputs=params, image=image)
        self.assertTrue(job.job_id())
        self.assertIsInstance(job, RuntimeJobV2)
        with mock_wait_for_final_state(service, job):
            job.wait_for_final_state()
            self.assertTrue(job.result())
        self.assertEqual(job.status(), "DONE")
        self.assertEqual(job.image, image)

    @run_cloud_fake
    def test_run_program_with_custom_log_level(self, service):
        """Test running program with a custom image."""
        job = run_program(service=service, log_level="DEBUG")
        job_raw = service._get_api_client()._get_job(job.job_id())
        self.assertEqual(job_raw.log_level, "DEBUG")

    @run_cloud_fake
    def test_run_program_failed(self, service):
        """Test a failed program execution."""
        job = run_program(service=service, job_classes=FailedRuntimeJob)
        with mock_wait_for_final_state(service, job):
            job.wait_for_final_state()
            job_result_raw = service._get_api_client().job_results(job.job_id())
            self.assertEqual("ERROR", job.status())
            self.assertEqual(
                API_TO_JOB_ERROR_MESSAGE["FAILED"].format(job.job_id(), job_result_raw),
                job.error_message(),
            )
            with self.assertRaises(RuntimeJobFailureError):
                job.result()

    @run_cloud_fake
    def test_run_program_failed_ran_too_long(self, service):
        """Test a program that failed since it ran longer than maximum execution time."""
        job = run_program(service=service, job_classes=FailedRanTooLongRuntimeJob)
        with mock_wait_for_final_state(service, job):
            job.wait_for_final_state()
            job_result_raw = service._get_api_client().job_results(job.job_id())
            self.assertEqual("ERROR", job.status())
            self.assertEqual(
                API_TO_JOB_ERROR_MESSAGE["CANCELLED - RAN TOO LONG"].format(
                    job.job_id(), job_result_raw
                ),
                job.error_message(),
            )
            with self.assertRaises(RuntimeJobMaxTimeoutError):
                job.result()

    @run_cloud_fake
    def test_cancel_job(self, service):
        """Test canceling a job."""
        job = run_program(service, job_classes=CancelableRuntimeJob)
        time.sleep(1)
        job.cancel()
        self.assertEqual(job.status(), "CANCELLED")
        rjob = service.job(job.job_id())
        self.assertEqual(rjob.status(), "CANCELLED")
        with self.assertRaises(RuntimeInvalidStateError) as exc:
            rjob.result()
        self.assertIn("Job was cancelled", str(exc.exception))

    @run_cloud_fake
    def test_final_result(self, service):
        """Test getting final result."""
        job = run_program(service)
        with mock_wait_for_final_state(service, job):
            result = job.result()
            self.assertTrue(result)

    @run_cloud_fake
    def test_job_status(self, service):
        """Test job status."""
        job = run_program(service)
        time.sleep(random.randint(1, 5))
        self.assertTrue(job.status())

    @run_cloud_fake
    def test_wait_for_final_state(self, service):
        """Test wait for final state."""
        job = run_program(service)
        with mock_wait_for_final_state(service, job):
            job.wait_for_final_state()
        self.assertEqual("DONE", job.status())

    @run_cloud_fake
    def test_delete_job(self, service):
        """Test deleting a job."""
        params = {"param1": "foo"}
        job = run_program(service=service, inputs=params)
        self.assertTrue(job.job_id())
        service.delete_job(job.job_id())
        with self.assertRaises(RuntimeJobNotFound):
            service.job(job.job_id())
