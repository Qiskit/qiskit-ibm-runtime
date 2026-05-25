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

import json
from unittest.mock import patch

from ddt import data, ddt

from qiskit_ibm_runtime.results.runner import RunnerResult
from qiskit_ibm_runtime.runtime_job_v2 import RuntimeJobV2

from ..ibm_test_case import IBMTestCase
from .mock.fake_runtime_client import BaseFakeRuntimeClient


@ddt
class TestRunner(IBMTestCase):
    """Test Runner results."""

    @data("circuit-runner", "qasm3-runner")
    def test_job_results(self, program):
        """Results for a Runner job should be a RunnerResult."""
        client = BaseFakeRuntimeClient()
        job = RuntimeJobV2(
            backend=None, api_client=client, job_id="123", program_id=program, service=None
        )
        job._status = "DONE"

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

        with patch.object(BaseFakeRuntimeClient, "job_results", return_value=results):
            result = job.result()
            self.assertIsInstance(result, RunnerResult)
