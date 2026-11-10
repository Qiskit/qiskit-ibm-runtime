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

import threading
from concurrent.futures import Future

import pytest
from qiskit.utils import optionals

from qiskit_ibm_runtime import EstimatorV2, SamplerV2
from qiskit_ibm_runtime.exceptions import RuntimeJobTimeoutError
from qiskit_ibm_runtime.executor import Executor
from qiskit_ibm_runtime.fake_provider import FakeManilaV2
from qiskit_ibm_runtime.fake_provider.local_runtime_job import LocalRuntimeJob
from qiskit_ibm_runtime.quantum_program import QuantumProgram
from qiskit_ibm_runtime.results import QuantumProgramResult
from qiskit_ibm_runtime.utils.converters import utc_to_local

from ...utils import get_primitive_inputs

if optionals.HAS_AER:
    from qiskit_aer import AerSimulator


class TestLocalRuntimeJob:
    """Class for testing local mode runtime jobs."""

    @pytest.mark.parametrize("primitive_class", [SamplerV2, EstimatorV2])
    def test_metrics_layout(self, primitive_class: type) -> None:
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
        assert (
            utc_to_local(metrics["timestamps"]["created"]).replace(tzinfo=None) == job.creation_date
        )

    @pytest.mark.parametrize("primitive_class", [SamplerV2, EstimatorV2])
    def test_status_done(self, primitive_class: type) -> None:
        """Test that a finished local job has the same status as a finished service job."""
        primitive = primitive_class(mode=FakeManilaV2())
        job = primitive.run(**get_primitive_inputs(primitive))
        job.wait_for_final_state()

        assert job.status() == "DONE"
        assert job.done()
        assert job.in_final_state()
        assert not job.errored()
        assert not job.running()
        assert not job.cancelled()

    def test_status_error(self) -> None:
        """Test the status of a failed local job."""

        def fail() -> None:
            raise ValueError("failed")

        job = LocalRuntimeJob(function=fail, backend=FakeManilaV2(), primitive="sampler", inputs={})
        job._submit()
        job.wait_for_final_state()

        assert job.status() == "ERROR"
        assert job.errored()
        assert job.in_final_state()
        assert not job.done()

    def test_status_before_final_state(self) -> None:
        """Test the status of a local job before it is in a final state."""
        backend = FakeManilaV2()
        job = LocalRuntimeJob(function=print, backend=backend, primitive="sampler", inputs={})
        assert job.status() == "INITIALIZING"

        job = LocalRuntimeJob(
            function=print, backend=backend, primitive="sampler", inputs={}, future=Future()
        )
        assert job.status() == "QUEUED"
        assert not job.in_final_state()

        job._future.set_running_or_notify_cancel()
        assert job.status() == "RUNNING"
        assert job.running()

        job._future.set_result(None)
        assert job.status() == "DONE"

    def test_status_cancelled(self) -> None:
        """Test the status of a cancelled local job."""
        job = LocalRuntimeJob(
            function=print, backend=FakeManilaV2(), primitive="sampler", inputs={}, future=Future()
        )
        assert job.cancel()

        assert job.status() == "CANCELLED"
        assert job.cancelled()
        assert job.in_final_state()

    def test_wait_for_final_state_timeout(self) -> None:
        """Test that waiting for a local job times out like waiting for a service job."""
        release = threading.Event()
        job = LocalRuntimeJob(
            function=release.wait, backend=FakeManilaV2(), primitive="sampler", inputs={}
        )
        job._submit()

        try:
            with pytest.raises(RuntimeJobTimeoutError):
                job.wait_for_final_state(timeout=0.1)
            assert not job.in_final_state()
        finally:
            # Let the job finish even if the test fails, so its thread does not block the exit.
            release.set()
        job.wait_for_final_state(timeout=10)
        assert job.status() == "DONE"

    def test_v2_sampler(self) -> None:
        """Test V2 Sampler on a local backend."""
        sampler = SamplerV2(mode=FakeManilaV2())
        job = sampler.run(**get_primitive_inputs(sampler))

        assert isinstance(job, LocalRuntimeJob)
        assert job.metrics()
        assert job.backend()
        assert job.inputs
        assert job.usage() == 0

    @pytest.mark.skipif(not optionals.HAS_AER, reason="qiskit-aer is required to run this test")
    def test_executor(self) -> None:
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
