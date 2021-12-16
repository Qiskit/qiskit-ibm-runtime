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

import time
import random

from qiskit.providers.jobstatus import JobStatus

from qiskit_ibm_runtime import RuntimeJob
from qiskit_ibm_runtime.constants import API_TO_JOB_ERROR_MESSAGE
from qiskit_ibm_runtime.exceptions import RuntimeJobFailureError

from .ibm_test_case import IBMTestCase
from .mock.fake_runtime_service import FakeRuntimeService
from .mock.fake_runtime_client import (FailedRuntimeJob,
                                       FailedRanTooLongRuntimeJob,
                                       CancelableRuntimeJob,
                                       CustomResultRuntimeJob)
from .utils.program import run_program, upload_program
from .utils.serialization import get_complex_types
from .decorators import run_legacy_and_cloud


class TestRunProgram(IBMTestCase):
    """Class for testing runtime modules."""

    def setUp(self):
        """Initial test setup."""
        super().setUp()
        self._legacy_service = FakeRuntimeService(auth="legacy", token="some_token")
        self._cloud_service = FakeRuntimeService(auth="cloud", token="some_token")

    @run_legacy_and_cloud
    def test_run_program(self, service):
        """Test running program."""
        params = {"param1": "foo"}
        job = run_program(service=service, inputs=params)
        self.assertTrue(job.job_id)
        self.assertIsInstance(job, RuntimeJob)
        self.assertIsInstance(job.status(), JobStatus)
        self.assertEqual(job.inputs, params)
        job.wait_for_final_state()
        self.assertEqual(job.status(), JobStatus.DONE)
        self.assertTrue(job.result())

    def test_run_program_with_custom_runtime_image(self):
        """Test running program with a custom image."""
        params = {"param1": "foo"}
        image = "name:tag"
        job = run_program(service=self._legacy_service, inputs=params, image=image)
        self.assertTrue(job.job_id)
        self.assertIsInstance(job, RuntimeJob)
        self.assertIsInstance(job.status(), JobStatus)
        self.assertEqual(job.inputs, params)
        job.wait_for_final_state()
        self.assertEqual(job.status(), JobStatus.DONE)
        self.assertTrue(job.result())
        self.assertEqual(job.image, image)

    def test_run_program_failed(self):
        """Test a failed program execution."""
        job = run_program(service=self._legacy_service, job_classes=FailedRuntimeJob)
        job.wait_for_final_state()
        job_result_raw = self._legacy_service._api_client.job_results(job.job_id)
        self.assertEqual(JobStatus.ERROR, job.status())
        self.assertEqual(
            API_TO_JOB_ERROR_MESSAGE["FAILED"].format(job.job_id, job_result_raw),
            job.error_message(),
        )
        with self.assertRaises(RuntimeJobFailureError):
            job.result()

    def test_run_program_failed_ran_too_long(self):
        """Test a program that failed since it ran longer than maximum execution time."""
        job = run_program(service=self._legacy_service, job_classes=FailedRanTooLongRuntimeJob)
        job.wait_for_final_state()
        job_result_raw = self._legacy_service._api_client.job_results(job.job_id)
        self.assertEqual(JobStatus.ERROR, job.status())
        self.assertEqual(
            API_TO_JOB_ERROR_MESSAGE["CANCELLED - RAN TOO LONG"].format(
                job.job_id, job_result_raw
            ),
            job.error_message(),
        )
        with self.assertRaises(RuntimeJobFailureError):
            job.result()

    def test_program_params_namespace(self):
        """Test running a program using parameter namespace."""
        service = self._legacy_service
        program_id = upload_program(service)
        params = service.program(program_id).parameters()
        params.param1 = "Hello World"
        run_program(service, program_id, inputs=params)

    def test_cancel_job(self):
        """Test canceling a job."""
        service = self._legacy_service
        job = run_program(service, job_classes=CancelableRuntimeJob)
        time.sleep(1)
        job.cancel()
        self.assertEqual(job.status(), JobStatus.CANCELLED)
        rjob = service.job(job.job_id)
        self.assertEqual(rjob.status(), JobStatus.CANCELLED)

    def test_final_result(self):
        """Test getting final result."""
        service = self._legacy_service
        job = run_program(service)
        result = job.result()
        self.assertTrue(result)

    def test_interim_results(self):
        """Test getting interim results."""
        service = self._legacy_service
        job = run_program(service)
        # TODO maybe a bit more validation on the returned interim results
        interim_results = job.interim_results()
        self.assertTrue(interim_results)

    def test_job_status(self):
        """Test job status."""
        service = self._legacy_service
        job = run_program(service)
        time.sleep(random.randint(1, 5))
        self.assertTrue(job.status())

    def test_job_inputs(self):
        """Test job inputs."""
        inputs = {"param1": "foo", "param2": "bar"}
        service = self._legacy_service
        job = run_program(service, inputs=inputs)
        self.assertEqual(inputs, job.inputs)

    def test_job_program_id(self):
        """Test job program ID."""
        service = self._legacy_service
        program_id = upload_program(service)
        job = run_program(service, program_id=program_id)
        self.assertEqual(program_id, job.program_id)

    def test_wait_for_final_state(self):
        """Test wait for final state."""
        service = self._legacy_service
        job = run_program(service)
        job.wait_for_final_state()
        self.assertEqual(JobStatus.DONE, job.status())

    def test_get_result_twice(self):
        """Test getting results multiple times."""
        service = self._legacy_service
        custom_result = get_complex_types()
        job_cls = CustomResultRuntimeJob
        job_cls.custom_result = custom_result

        job = run_program(service=service, job_classes=job_cls)
        _ = job.result()
        _ = job.result()
