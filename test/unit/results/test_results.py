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

"""Tests for the results module."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Literal

import pytest

from qiskit_ibm_runtime.qiskit_runtime_service import QiskitRuntimeService
from qiskit_ibm_runtime.results.runner import RunnerResult

from ...registries import Job

if TYPE_CHECKING:
    from ...registries import BaseRegistry


class TestRunner:
    """Test Runner results."""

    @pytest.mark.parametrize("program", ["circuit-runner", "qasm3-runner"])
    def test_job_results(
        self, program: Literal["sampler", "estimator", "executor"], registry: BaseRegistry
    ) -> None:
        """Results for a Runner job should be a RunnerResult."""
        # Excerpt from running a job in aer, and extracting the `results` key (without `metadata`)
        # of `job.results().to_dict()`
        results = json.dumps(
            {
                "results": [
                    {
                        "shots": 1024,
                        "success": True,
                        "data": {"counts": {"0x0": 492, "0x1": 532}},
                        "meas_level": 2,
                        "header": {
                            "creg_sizes": [["c", 1]],
                            "global_phase": 0.0,
                            "memory_slots": 1,
                            "n_qubits": 1,
                            "name": "circuit-41",
                            "qreg_sizes": [["q", 1]],
                            "metadata": {},
                        },
                        "status": "DONE",
                        "seed_simulator": 3137632464,
                    }
                ]
            }
        )

        registry.add_job(Job("my_job", "common_backend", program=program, raw_results=results), "a")

        service = QiskitRuntimeService(token="my_token")
        job = service.job("my_job")
        result = job.result()
        assert isinstance(result, RunnerResult)
