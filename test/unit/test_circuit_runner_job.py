# This code is part of Qiskit.
#
# (C) Copyright IBM 2023.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Tests for circuit runner job."""

from typing import Any, Optional
from unittest.mock import MagicMock

import numpy as np
from qiskit.providers.jobstatus import JOB_FINAL_STATES, JobStatus

from qiskit_ibm_runtime import RuntimeJob
from qiskit_ibm_runtime.utils.runner_result import RunnerResult

from ..ibm_test_case import IBMTestCase


class FakeCircuitRunnerJob(RuntimeJob):
    """Class for faking a circuit runner job."""

    def __init__(self, data: Any) -> None:
        """
        Args:
            data: the raw data of results
        """
        self._data = data
        api_client = MagicMock()
        api_client.job_results = MagicMock(return_value=self._data)
        client_params = MagicMock()
        backend = job_id = program_id = service = None
        super().__init__(
            backend,
            api_client,
            client_params,
            job_id,
            program_id,
            service,
            result_decoder=RunnerResult,
        )

    def wait_for_final_state(self, timeout: Optional[float] = None) -> None:
        """Fake wait

        Args:
            timeout: ignored
        """
        return

    def status(self) -> JobStatus:
        """Return the status of the job.

        Returns:
            Status of this job.
        """
        return JOB_FINAL_STATES

    def submit(self) -> None:
        """Fake submit"""
        pass


class TestCircuitRunnerJobIBMTestCase(IBMTestCase):
    """Class for testing circuit runner job result"""

    def test_circuit_metadata_ndarray(self):
        """Test circuit metadata with ndarray"""
        data = (
            '{"backend_name": "qasm_simulator", "backend_version": "0.12.0", '
            '"date": "2023-08-07T09:02:07.066699", "header": null, "qobj_id": "", '
            '"job_id": "dd1f21b5-3bfe-4a47-a572-32955dca518f", "status": "COMPLETED", '
            '"success": true, "results": [{"shots": 1024, "success": true, '
            '"data": {"counts": {"0x0": 1024}}, "meas_level": 2, '
            '"header": {"creg_sizes": [["meas", 1]], "global_phase": 0.0, "memory_slots": 1, '
            '"metadata": {"array": {"__type__": "ndarray", "__value__": '
            '"eJyb7BfqGxDJyFDGUK2eklqcXKRupaBuk2ahrqOgnpZfVFKUmBefX5SSChJ3S8wpTgWKF2ckFqQC+'
            'RpGOgpGmjoKtQpkAy4GMPhgz4AVfLAHAOaIHc0="}}, "n_qubits": 1, "name": "circuit-127", '
            '"qreg_sizes": [["q", 1]]}, "status": "DONE", "seed_simulator": 2210027864, '
            '"metadata": {"parallel_state_update": 16, "sample_measure_time": 0.000280283, '
            '"noise": "ideal", "batched_shots_optimization": false, "measure_sampling": true, '
            '"device": "CPU", "num_qubits": 1, "parallel_shots": 1, "remapped_qubits": false, '
            '"method": "stabilizer", "active_input_qubits": [0], "num_clbits": 1, '
            '"input_qubit_map": [[0, 0]], "fusion": {"enabled": false}}, "time_taken": 0.001479539}], '
            '"metadata": {"time_taken_execute": 0.001518685, "mpi_rank": 0, '
            '"parallel_experiments": 1, "omp_enabled": true, "max_gpu_memory_mb": 0, '
            '"num_processes_per_experiments": 1, "num_mpi_processes": 1, "max_memory_mb": 64098}, '
            '"time_taken": 0.0019528865814208984}'
        )
        job = FakeCircuitRunnerJob(data)
        result = job.result()
        metadata = result.results[0].header.metadata
        self.assertIn("array", metadata)
        np.testing.assert_allclose(metadata["array"], [[1, 0], [0, 1]])
