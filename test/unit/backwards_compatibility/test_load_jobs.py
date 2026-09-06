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

"""Tests for backwards compatibility when loading jobs from earlier versions."""

from pathlib import Path

from qiskit_ibm_runtime.fake_provider import FakeFez
from qiskit_ibm_runtime.qiskit_runtime_service import QiskitRuntimeService
from qiskit_ibm_runtime.results.quantum_program import QuantumProgramResult

from ...decorators import mock_responses
from ...ibm_test_case import IBMTestCase
from ...registries import Backend, Job, OneInstanceNoBackendsRegistry


class StoredJobsTestCase(IBMTestCase):
    """Test for loading stored jobs from earlier versions."""

    @mock_responses(OneInstanceNoBackendsRegistry)
    def test_executor_jobs(self, registry: OneInstanceNoBackendsRegistry) -> None:
        """Test stored Executor jobs."""
        job_id = "da66nicgd8dc73doc6mg"

        resources_path = Path(__file__).resolve().parent / "resources"
        job_details = (resources_path / f"{job_id}_details.json").read_text(encoding="utf-8")
        job_results = (resources_path / f"{job_id}_results.json").read_text(encoding="utf-8")

        # Prepare the contents of the registry.
        registry.add_backend(Backend.from_(FakeFez))
        registry.add_job(
            Job(job_id, "ibm_fez", raw_details=job_details, raw_results=job_results), "a"
        )

        service = QiskitRuntimeService(token="my_token")
        job = service.job(job_id)
        result = job.result()

        # Job should be an executor (wrapped sampler) job.
        self.assertEqual(job.primitive_id, "executor")
        # Result should be loaded correctly.
        self.assertIsInstance(result, QuantumProgramResult)
