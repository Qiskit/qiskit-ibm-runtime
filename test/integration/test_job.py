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

from __future__ import annotations

import random
import time
from typing import TYPE_CHECKING

import pytest
from qiskit.providers.exceptions import QiskitBackendNotFoundError

from qiskit_ibm_runtime.exceptions import (
    IBMRuntimeError,
    RuntimeInvalidStateError,
    RuntimeJobNotFound,
)

from .utils import cancel_job_safe, wait_for_status

if TYPE_CHECKING:
    from collections.abc import Callable

    from qiskit_ibm_runtime import IBMBackend, RuntimeJobV2

    from .dependencies import Dependencies


class TestIntegrationJob:
    """Integration tests for job functions."""

    def test_run_program(self, submit_bell_job: Callable[..., RuntimeJobV2]) -> None:
        """Test running a program."""
        job = submit_bell_job()
        job.wait_for_final_state()
        assert "DONE" == job.status()
        assert job.result()

    def test_run_with_simplejson(self, submit_bell_job: Callable[..., RuntimeJobV2]) -> None:
        """Test retrieving job results with simplejson package installed."""
        try:
            __import__("simplejson")
        except ImportError:
            pytest.skip("simplejson is not installed")

        job = submit_bell_job()
        job.wait_for_final_state()
        assert job.result()

    @pytest.mark.production
    def test_cancel_job_queued(
        self,
        submit_bell_job: Callable[..., RuntimeJobV2],
        dependencies: Dependencies,
    ) -> None:
        """Test canceling a queued job."""
        service = dependencies.service
        _ = submit_bell_job()
        job = submit_bell_job()
        wait_for_status(job, "QUEUED")
        if not cancel_job_safe(job):
            return
        time.sleep(15)  # Wait a bit for DB to update.
        rjob = service.job(job.job_id())
        assert rjob.status() == "CANCELLED"

    def test_cancel_job_running(
        self,
        submit_bell_job: Callable[..., RuntimeJobV2],
        dependencies: Dependencies,
    ) -> None:
        """Test canceling a running job."""
        service = dependencies.service
        job = submit_bell_job()
        rjob = service.job(job.job_id())
        if not cancel_job_safe(rjob):
            return
        time.sleep(5)
        assert rjob.status() == "CANCELLED"

    def test_cancel_job_done(self, submit_bell_job: Callable[..., RuntimeJobV2]) -> None:
        """Test canceling a finished job."""
        job = submit_bell_job()
        job.wait_for_final_state()
        with pytest.raises(RuntimeInvalidStateError):
            job.cancel()

    def test_delete_job(
        self,
        submit_bell_job: Callable[..., RuntimeJobV2],
        dependencies: Dependencies,
    ) -> None:
        """Test deleting a job."""
        service = dependencies.service
        job = submit_bell_job()
        wait_for_status(job, "DONE")
        try:
            service.delete_job(job.job_id())
        except IBMRuntimeError as ex:
            if "403 Client Error" in ex.message or "401 Client Error" in ex.message:
                pytest.skip("Credentials do not have delete job privileges")
        with pytest.raises(RuntimeJobNotFound):
            service.job(job.job_id())

    @pytest.mark.production
    def test_delete_job_queued(
        self,
        submit_bell_job: Callable[..., RuntimeJobV2],
        dependencies: Dependencies,
    ) -> None:
        """Test deleting a queued job."""
        service = dependencies.service
        try:
            real_device_name = service.least_busy(simulator=False).name
        except QiskitBackendNotFoundError:
            pytest.skip("No real device found in the instance")
        _ = submit_bell_job(backend_name=real_device_name)
        job = submit_bell_job(backend_name=real_device_name)
        wait_for_status(job, "QUEUED")
        try:
            service.delete_job(job.job_id())
        except IBMRuntimeError as ex:
            if "403 Client Error" in ex.message or "401 Client Error" in ex.message:
                pytest.skip("Credentials do not have delete job privileges")
        with pytest.raises(RuntimeJobNotFound):
            service.job(job.job_id())

    def test_job_status(self, submit_bell_job: Callable[..., RuntimeJobV2]) -> None:
        """Test job status."""
        job = submit_bell_job()
        time.sleep(random.randint(1, 5))
        assert job.status()

    def test_job_backend(
        self, submit_bell_job: Callable[..., RuntimeJobV2], backend_test: IBMBackend | None
    ) -> None:
        """Test job backend."""
        job = submit_bell_job()
        assert backend_test.name == job.backend().name

    def test_job_program_id(self, submit_bell_job: Callable[..., RuntimeJobV2]) -> None:
        """Test job program ID."""
        job = submit_bell_job()
        assert "sampler" == job.primitive_id

    def test_wait_for_final_state(
        self,
        submit_bell_job: Callable[..., RuntimeJobV2],
        dependencies: Dependencies,
    ) -> None:
        """Test wait for final state."""
        job = submit_bell_job(backend_name=dependencies.qpu)
        job.wait_for_final_state()
        assert "DONE" == job.status()

    def test_wait_for_final_state_after_job_status(
        self,
        submit_bell_job: Callable[..., RuntimeJobV2],
        dependencies: Dependencies,
    ) -> None:
        """Test wait for final state on a completed job when the status is updated first."""
        job = submit_bell_job(backend_name=dependencies.qpu)
        status = job.status()
        while status not in ["DONE", "CANCELLED", "ERROR"]:
            status = job.status()
        job.wait_for_final_state()
        assert "DONE" == job.status()

    def test_job_creation_date(
        self,
        submit_bell_job: Callable[..., RuntimeJobV2],
        dependencies: Dependencies,
    ) -> None:
        """Test job creation date."""
        service = dependencies.service
        job = submit_bell_job()
        assert job.creation_date
        rjob = service.job(job.job_id())
        assert rjob.creation_date
        rjobs = service.jobs(limit=2)
        for rjob in rjobs:
            assert rjob.creation_date

    def test_job_metrics(self, submit_bell_job: Callable[..., RuntimeJobV2]) -> None:
        """Test job metrics."""
        job = submit_bell_job()
        job.wait_for_final_state()
        metrics = job.metrics()
        assert metrics
        assert "timestamps" in metrics
        assert "qiskit_version" in metrics

    def test_usage_estimation(self, submit_bell_job: Callable[..., RuntimeJobV2]) -> None:
        """Test job usage estimation."""
        job = submit_bell_job()
        job.wait_for_final_state()
        assert job.usage_estimation
        assert "quantum_seconds" in job.usage_estimation

    def test_job_usage(self, submit_bell_job: Callable[..., RuntimeJobV2]) -> None:
        """Test job usage."""
        job = submit_bell_job()
        job.wait_for_final_state()
        assert isinstance(job.usage(), (float, int))

    def test_job_logs(self, submit_bell_job: Callable[..., RuntimeJobV2]) -> None:
        """Test job logs."""
        job = submit_bell_job()
        job.wait_for_final_state()
        assert isinstance(job.logs(), str)

    def test_updating_job_tags(self, submit_bell_job: Callable[..., RuntimeJobV2]) -> None:
        """Test job metrics."""
        job = submit_bell_job(job_tags=["test_tag123"])
        job.wait_for_final_state()
        new_job_tag = ["new_test_tag"]
        job.update_tags(new_job_tag)
        assert set(job.tags) == set(new_job_tag)

    def test_circuit_params_not_stored(self, submit_bell_job: Callable[..., RuntimeJobV2]) -> None:
        """Test that circuits are not automatically stored in the job params."""
        job = submit_bell_job()
        job.wait_for_final_state()
        assert not hasattr(job, "_params")
        assert job.inputs
