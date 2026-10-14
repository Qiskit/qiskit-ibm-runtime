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

"""Helpers for the integration tests.

These require a live service, so they are kept out of the shared `test.utils` module.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from qiskit_ibm_runtime.runtime_job_v2 import RuntimeJobV2


def wait_for_status(job: RuntimeJobV2, status: str, poll_time: int = 1, time_out: int = 20) -> None:
    """Wait for job to reach a certain status."""
    wait_time = 1 if status == "QUEUED" else poll_time
    while job.status() not in ["DONE", "CANCELLED", "ERROR", status] and time_out > 0:
        time.sleep(wait_time)
        time_out -= wait_time
    if job.status() != status:
        pytest.skip(f"Job {job.job_id()} unable to reach status {status}.")
