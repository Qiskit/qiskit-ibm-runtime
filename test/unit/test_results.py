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

from qiskit_ibm_runtime.runtime_job_v2 import RuntimeJobV2
from qiskit_ibm_runtime.results.runner import RunnerResult

from .mock.fake_runtime_client import BaseFakeRuntimeClient
from ..ibm_test_case import IBMTestCase

RESULTS = {
    "results": [
        {
            "shots": 1024,
            "success": True,
            "data": {"counts": {"0x1": 530, "0x0": 494}},
            "meas_level": 2,
        }
    ]
}


class TestRunner(IBMTestCase):
    """Test Runner results."""

    def test_job_results(self):
        """Results for a Runner job should be a RunnerResult."""
        client = BaseFakeRuntimeClient()
        job = RuntimeJobV2(
            backend=None, api_client=client, job_id="123", program_id="circuit-runner", service=None
        )
        job._status = "DONE"

        with patch.object(BaseFakeRuntimeClient, "job_results", return_value=json.dumps(RESULTS)):
            result = job.result()
            self.assertIsInstance(result, RunnerResult)

