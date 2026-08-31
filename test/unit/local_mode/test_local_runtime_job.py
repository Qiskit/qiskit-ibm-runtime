# This code is part of Qiskit.
#
# (C) Copyright IBM 2024-2026.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Tests for local mode."""

from unittest import skipUnless

from qiskit.utils import optionals

from qiskit_ibm_runtime import SamplerV2
from qiskit_ibm_runtime.executor import Executor
from qiskit_ibm_runtime.fake_provider import FakeManilaV2
from qiskit_ibm_runtime.fake_provider.local_runtime_job import LocalRuntimeJob
from qiskit_ibm_runtime.quantum_program import QuantumProgram
from qiskit_ibm_runtime.results import QuantumProgramResult

from ...ibm_test_case import IBMTestCase
from ...utils import get_primitive_inputs

if optionals.HAS_AER:
    from qiskit_aer import AerSimulator


class TestLocalRuntimeJob(IBMTestCase):
    """Class for testing local mode runtime jobs."""

    def test_v2_sampler(self):
        """Test V2 Sampler on a local backend."""
        sampler = SamplerV2(mode=FakeManilaV2())
        job = sampler.run(**get_primitive_inputs(sampler))

        self.assertIsInstance(job, LocalRuntimeJob)
        self.assertTrue(job.metrics())
        self.assertTrue(job.backend())
        self.assertTrue(job.inputs)
        self.assertEqual(job.usage(), 0)

    @skipUnless(condition=optionals.HAS_AER, reason="qiskit-aer is required to run this test")
    def test_executor(self):
        """Test executor on a local backend."""
        executor = Executor(
            AerSimulator(method="stabilizer"),
            options={
                "experimental": {
                    "local_mode": True,
                }
            },
        )
        job = executor.run(QuantumProgram(1))
        self.assertIsInstance(job, LocalRuntimeJob)
        self.assertTrue(job.metrics())
        self.assertTrue(job.backend())
        self.assertTrue(job.inputs)
        self.assertEqual(job.usage(), 0)

        # Specific to executor jobs.
        self.assertIsInstance(job.inputs, QuantumProgram)
        self.assertIsInstance(job.result(), QuantumProgramResult)
