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

"""Tests for job functions using real runtime service."""

import logging
import random
import time

from qiskit_ibm_runtime.exceptions import (
    IBMRuntimeError,
    RuntimeInvalidStateError,
    RuntimeJobNotFound,
)

from ..decorators import production_only
from ..utils import cancel_job_safe, get_real_device, wait_for_status
from .case import IBMIntegrationJobTestCase

logger = logging.getLogger(__name__)


class TestIntegrationJob(IBMIntegrationJobTestCase):
    """Integration tests for job functions."""

    def test_run_program(self):
        """Test running a program."""
        service = self.service
        job = self.submit_bell_job(service)
        job.wait_for_final_state()
        self.assertEqual("DONE", job.status())
        self.assertTrue(job.result())

    def test_run_with_simplejson(self):
        """Test retrieving job results with simplejson package installed."""
        service = self.service
        try:
            __import__("simplejson")
            job = self.submit_bell_job(service=service)
            job.wait_for_final_state()
            self.assertTrue(job.result())
        except ImportError:
            self.assertRaises(ImportError)

    @production_only
    def test_cancel_job_queued(self):
        """Test canceling a queued job."""
        service = self.service
        _ = self.submit_bell_job(
            service,
        )
        job = self.submit_bell_job(service)
        wait_for_status(job, "QUEUED")
        if not cancel_job_safe(job, logger):
            return
        time.sleep(15)  # Wait a bit for DB to update.
        rjob = service.job(job.job_id())
        self.assertEqual(rjob.status(), "CANCELLED")

    def test_cancel_job_running(self):
        """Test canceling a running job."""
        service = self.service
        job = self.submit_bell_job(
            service,
        )
        rjob = service.job(job.job_id())
        if not cancel_job_safe(rjob, logger):
            return
        time.sleep(5)
        self.assertEqual(rjob.status(), "CANCELLED")

    def test_cancel_job_done(self):
        """Test canceling a finished job."""
        service = self.service
        job = self.submit_bell_job(service)
        job.wait_for_final_state()
        with self.assertRaises(RuntimeInvalidStateError):
            job.cancel()

    def test_delete_job(self):
        """Test deleting a job."""
        service = self.service
        job = self.submit_bell_job(service)
        wait_for_status(job, "DONE")
        try:
            service.delete_job(job.job_id())
        except IBMRuntimeError as ex:
            if "403 Client Error" in ex.message or "401 Client Error" in ex.message:
                self.skipTest("Credentials do not have delete job privileges")
        with self.assertRaises(RuntimeJobNotFound):
            service.job(job.job_id())

    @production_only
    def test_delete_job_queued(self):
        """Test deleting a queued job."""
        service = self.service
        real_device_name = get_real_device(service)
        _ = self.submit_bell_job(service, backend_name=real_device_name)
        job = self.submit_bell_job(service, backend_name=real_device_name)
        wait_for_status(job, "QUEUED")
        try:
            service.delete_job(job.job_id())
        except IBMRuntimeError as ex:
            if "403 Client Error" in ex.message or "401 Client Error" in ex.message:
                self.skipTest("Credentials do not have delete job privileges")
        with self.assertRaises(RuntimeJobNotFound):
            service.job(job.job_id())

    def test_job_status(self):
        """Test job status."""
        service = self.service
        job = self.submit_bell_job(service)
        time.sleep(random.randint(1, 5))
        self.assertTrue(job.status())

    def test_job_backend(self):
        """Test job backend."""
        service = self.service
        job = self.submit_bell_job(service)
        self.assertEqual(self.test_backend.name, job.backend().name)

    def test_job_program_id(self):
        """Test job program ID."""
        service = self.service
        job = self.submit_bell_job(service)
        self.assertEqual("sampler", job.primitive_id)

    def test_wait_for_final_state(self):
        """Test wait for final state."""
        service = self.service
        job = self.submit_bell_job(service, backend_name=self.dependencies.qpu)
        job.wait_for_final_state()
        self.assertEqual("DONE", job.status())

    def test_wait_for_final_state_after_job_status(self):
        """Test wait for final state on a completed job when the status is updated first."""
        service = self.service
        job = self.submit_bell_job(service, backend_name=self.dependencies.qpu)
        status = job.status()
        while status not in ["DONE", "CANCELLED", "ERROR"]:
            status = job.status()
        job.wait_for_final_state()
        self.assertEqual("DONE", job.status())

    def test_job_creation_date(self):
        """Test job creation date."""
        service = self.service
        job = self.submit_bell_job(service)
        self.assertTrue(job.creation_date)
        rjob = service.job(job.job_id())
        self.assertTrue(rjob.creation_date)
        rjobs = service.jobs(limit=2)
        for rjob in rjobs:
            self.assertTrue(rjob.creation_date)

    def test_job_metrics(self):
        """Test job metrics."""
        service = self.service
        job = self.submit_bell_job(service)
        job.wait_for_final_state()
        metrics = job.metrics()
        self.assertTrue(metrics)
        self.assertIn("timestamps", metrics)
        self.assertIn("qiskit_version", metrics)

    def test_usage_estimation(self):
        """Test job usage estimation."""
        service = self.service
        job = self.submit_bell_job(service)
        job.wait_for_final_state()
        self.assertTrue(job.usage_estimation)
        self.assertIn("quantum_seconds", job.usage_estimation)

    def test_job_usage(self):
        """Test job usage."""
        service = self.service
        job = self.submit_bell_job(service)
        job.wait_for_final_state()
        self.assertIsInstance(job.usage(), (float, int))

    def test_job_logs(self):
        """Test job logs."""
        service = self.service
        job = self.submit_bell_job(service)
        job.wait_for_final_state()
        self.assertIsInstance(job.logs(), str)

    def test_updating_job_tags(self):
        """Test job metrics."""
        service = self.service
        job = self.submit_bell_job(service, job_tags=["test_tag123"])
        job.wait_for_final_state()
        new_job_tag = ["new_test_tag"]
        job.update_tags(new_job_tag)
        self.assertTrue(job.tags, new_job_tag)

    def test_circuit_params_not_stored(self):
        """Test that circuits are not automatically stored in the job params."""
        service = self.service
        job = self.submit_bell_job(service)
        job.wait_for_final_state()
        self.assertFalse(hasattr(job, "_params"))
        self.assertTrue(job.inputs)
