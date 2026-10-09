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

from ddt import data, ddt
from qiskit.utils import optionals

from qiskit_ibm_runtime import EstimatorV2, SamplerV2
from qiskit_ibm_runtime.executor import Executor
from qiskit_ibm_runtime.fake_provider import FakeManilaV2
from qiskit_ibm_runtime.fake_provider.local_runtime_job import LocalRuntimeJob
from qiskit_ibm_runtime.quantum_program import QuantumProgram
from qiskit_ibm_runtime.results import QuantumProgramResult
from qiskit_ibm_runtime.utils.converters import utc_to_local

from ...ibm_test_case import IBMTestCase
from ...utils import get_primitive_inputs

if optionals.HAS_AER:
    from qiskit_aer import AerSimulator


@ddt
class TestLocalRuntimeJob(IBMTestCase):
    """Class for testing local mode runtime jobs."""

    @data(SamplerV2, EstimatorV2)
    def test_metrics_layout(self, primitive_class):
        """Test that local job metrics have the same layout as metrics of a service job."""
        primitive = primitive_class(mode=FakeManilaV2())
        job = primitive.run(**get_primitive_inputs(primitive))
        job.result()
        metrics = job.metrics()

        assert metrics["usage"] == {"qpu_charge_time_seconds": 0, "status": "complete"}
        assert "bss" not in metrics
        for name in ("created", "running", "finished"):
            assert isinstance(metrics["timestamps"][name], str)
            assert metrics["timestamps"][name].endswith("Z")
        # The UTC timestamps convert back to the job's local creation time.
        assert utc_to_local(metrics["timestamps"]["created"]).replace(tzinfo=None) == job.creation_date

    def test_v2_sampler(self):
        """Test V2 Sampler on a local backend."""
        sampler = SamplerV2(mode=FakeManilaV2())
        job = sampler.run(**get_primitive_inputs(sampler))

        assert isinstance(job, LocalRuntimeJob)
        assert job.metrics()
        assert job.backend()
        assert job.inputs
        assert job.usage() == 0

    @skipUnless(condition=optionals.HAS_AER, reason="qiskit-aer is required to run this test")
    def test_executor(self):
        """Test executor on a local backend."""
        executor = Executor(AerSimulator(method="stabilizer"))
        job = executor.run(QuantumProgram(1))
        assert isinstance(job, LocalRuntimeJob)
        assert job.metrics()
        assert job.backend()
        assert job.inputs
        assert job.usage() == 0

        # Specific to executor jobs.
        assert isinstance(job.inputs, QuantumProgram)
        assert isinstance(job.result(), QuantumProgramResult)
