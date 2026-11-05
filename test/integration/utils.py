# This code is part of Qiskit.
#
# (C) Copyright IBM 2026.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Helpers for the integration tests."""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

import pytest
from qiskit.compiler import transpile

from qiskit_ibm_runtime import SamplerV2
from qiskit_ibm_runtime.exceptions import RuntimeInvalidStateError

from ..utils import bell

if TYPE_CHECKING:
    from qiskit_ibm_runtime import IBMBackend
    from qiskit_ibm_runtime.runtime_job_v2 import RuntimeJobV2

logger = logging.getLogger(__name__)


def wait_for_status(job: RuntimeJobV2, status: str, poll_time: int = 1, time_out: int = 20) -> None:
    """Wait for job to reach a certain status."""
    wait_time = 1 if status == "QUEUED" else poll_time
    while job.status() not in ["DONE", "CANCELLED", "ERROR", status] and time_out > 0:
        time.sleep(wait_time)
        time_out -= wait_time
    if job.status() != status:
        pytest.skip(f"Job {job.job_id()} unable to reach status {status}.")


def cancel_job_safe(job: RuntimeJobV2) -> bool:
    """Cancel a runtime job."""
    try:
        job.cancel()
        status = job.status()
        if status != "CANCELLED":
            raise AssertionError(
                f"cancel() was successful for job {job.job_id()} but its status is {status}."
            )
        return True
    except RuntimeInvalidStateError:
        if job.status() in ["DONE", "CANCELLED", "ERROR"]:
            logger.warning("Unable to cancel job because it's already done.")
            return False
        raise


def submit_and_cancel(backend: IBMBackend) -> RuntimeJobV2:
    """Submit a bell job to `backend` and cancel it, returning the cancelled job."""
    circuit = transpile(bell(), backend=backend)
    sampler = SamplerV2(backend)
    job = sampler.run([circuit])
    cancel_job_safe(job)

    return job
