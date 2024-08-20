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

from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

from qiskit_ibm_runtime.exceptions import (
    RuntimeInvalidStateError,
    RuntimeJobNotFound,
)

from ..ibm_test_case import IBMIntegrationJobTestCase
from ..decorators import run_integration_test, production_only, quantum_only
from ..serialization import (
    SerializableClass,
)
from ..utils import cancel_job_safe, wait_for_status, get_real_device, bell


class TestIntegrationJob(IBMIntegrationJobTestCase):
    """Integration tests for job functions."""

    @run_integration_test
    def test_run_program(self, service):
        """Test running a program."""
        job = self._run_program(service)
        job.wait_for_final_state()
        self.assertEqual("DONE", job.status())
        self.assertTrue(job.result())

    @run_integration_test
    def test_run_with_simplejson(self, service):
        """Test retrieving job results with simplejson package installed."""
        try:
            __import__("simplejson")
            job = self._run_program(service=service)
            job.wait_for_final_state()
            self.assertTrue(job.result())
        except ImportError:
            self.assertRaises(ImportError)

    @run_integration_test
    @quantum_only
    def test_run_program_log_level(self, service):
        """Test running with a custom log level."""
        levels = ["INFO", "ERROR"]
        for level in levels:
            with self.subTest(level=level):
                job = self._run_program(service, log_level=level)
                job.wait_for_final_state()
                if job.logs():
                    self.assertIn("Completed", job.logs())

    @run_integration_test
    @production_only
    def test_cancel_job_queued(self, service):
        """Test canceling a queued job."""
        real_device_name = get_real_device(service)
        real_device = service.backend(real_device_name)
        pm = generate_preset_pass_manager(optimization_level=1, target=real_device.target)
        _ = self._run_program(service, circuits=pm.run([bell()] * 10), backend=real_device_name)
        job = self._run_program(service, circuits=pm.run([bell()] * 2), backend=real_device_name)
        wait_for_status(job, "QUEUED")
        if not cancel_job_safe(job, self.log):
            return
        time.sleep(15)  # Wait a bit for DB to update.
        rjob = service.job(job.job_id())
        self.assertEqual(rjob.status(), "CANCELLED")

    @run_integration_test
    def test_cancel_job_running(self, service):
        """Test canceling a running job."""
        job = self._run_program(
            service,
        )
        rjob = service.job(job.job_id())
        if not cancel_job_safe(rjob, self.log):
            return
        time.sleep(5)
        self.assertEqual(rjob.status(), "CANCELLED")

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
        sub_tests = ["DONE"]
        for status in sub_tests:
            with self.subTest(status=status):
                job = self._run_program(service)
                wait_for_status(job, status)
                service.delete_job(job.job_id())
                with self.assertRaises(RuntimeJobNotFound):
                    service.job(job.job_id())

    @run_integration_test
    @production_only
    def test_delete_job_queued(self, service):
        """Test deleting a queued job."""
        real_device_name = get_real_device(service)
        real_device = service.backend(real_device_name)
        pm = generate_preset_pass_manager(optimization_level=1, target=real_device.target)
        isa_circuit = pm.run([bell()])
        _ = self._run_program(service, circuits=isa_circuit, backend=real_device_name)
        job = self._run_program(service, circuits=isa_circuit, backend=real_device_name)
        wait_for_status(job, "QUEUED")
        service.delete_job(job.job_id())
        with self.assertRaises(RuntimeJobNotFound):
            service.job(job.job_id())

    @run_integration_test
    def test_job_status(self, service):
        """Test job status."""
        job = self._run_program(service)
        time.sleep(random.randint(1, 5))
        self.assertTrue(job.status())

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
        job = self._run_program(service, backend="ibmq_qasm_simulator")
        job.wait_for_final_state()
        self.assertEqual("DONE", job.status())

    @run_integration_test
    @production_only
    def test_run_program_missing_backend_ibm_cloud(self, service):
        """Test running an ibm_cloud program with no backend."""
        if self.dependencies.channel == "ibm_quantum":
            self.skipTest("Not supported on ibm_quantum")
        with self.subTest():
            job = self._run_program(service=service, backend="")
            _ = job.status()
            self.assertTrue(job.backend())

    @run_integration_test
    def test_wait_for_final_state_after_job_status(self, service):
        """Test wait for final state on a completed job when the status is updated first."""
        job = self._run_program(service, backend="ibmq_qasm_simulator")
        status = job.status()
        while status not in ["DONE", "CANCELLED", "ERROR"]:
            status = job.status()
        job.wait_for_final_state()
        self.assertEqual("DONE", job.status())

    @run_integration_test
    def test_job_creation_date(self, service):
        """Test job creation date."""
        job = self._run_program(service)
        self.assertTrue(job.creation_date)
        rjob = service.job(job.job_id())
        self.assertTrue(rjob.creation_date)
        rjobs = service.jobs(limit=2)
        for rjob in rjobs:
            self.assertTrue(rjob.creation_date)

    @run_integration_test
    def test_job_metrics(self, service):
        """Test job metrics."""
        job = self._run_program(service)
        job.wait_for_final_state()
        metrics = job.metrics()
        self.assertTrue(metrics)
        self.assertIn("timestamps", metrics)
        self.assertIn("qiskit_version", metrics)

    @run_integration_test
    def test_usage_estimation(self, service):
        """Test job usage estimation"""
        job = self._run_program(service)
        job.wait_for_final_state()
        self.assertTrue(job.usage_estimation)
        self.assertIn("quantum_seconds", job.usage_estimation)

    @run_integration_test
    def test_updating_job_tags(self, service):
        """Test job metrics."""
        job = self._run_program(service, job_tags=["test_tag123"])
        job.wait_for_final_state()
        new_job_tag = ["new_test_tag"]
        job.update_tags(new_job_tag)
        self.assertTrue(job.tags, new_job_tag)

    @run_integration_test
    def test_circuit_params_not_stored(self, service):
        """Test that circuits are not automatically stored in the job params."""
        job = self._run_program(service)
        job.wait_for_final_state()
        self.assertFalse(hasattr(job, "_params"))
        self.assertTrue(job.inputs)

    def _assert_complex_types_equal(self, expected, received):
        """Verify the received data in complex types is expected."""
        if "serializable_class" in received:
            received["serializable_class"] = SerializableClass.from_json(
                received["serializable_class"]
            )
        self.assertEqual(expected, received)
