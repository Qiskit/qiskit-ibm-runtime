# This code is part of Qiskit.
#
# (C) Copyright IBM 2022-2026.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Tests for client-side noise learner."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from qiskit.circuit import Parameter, QuantumCircuit
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from samplomatic.transpiler import generate_boxing_pass_manager
from samplomatic.utils import find_unique_box_instructions

from qiskit_ibm_runtime.executor_noise_learner import NoiseLearnerV3
from qiskit_ibm_runtime.results import NoiseLearnerV3Result, NoiseLearnerV3Results
from qiskit_ibm_runtime.utils.utils import HAS_QNL

if TYPE_CHECKING:
    from .dependencies import Dependencies


@pytest.mark.skipif(not HAS_QNL, reason="qiskit-noise-learning is required to run this test")
class TestNoiseLearnerV3:
    """Test client-side NLV3."""

    def test_noise_learner_v3(self, dependencies: Dependencies) -> None:
        """Test NLV3 with basic options."""
        backend = dependencies.service.backend(dependencies.qpu)

        boxing_pass_manager = generate_preset_pass_manager(backend=backend, optimization_level=0)
        boxing_pass_manager.post_scheduling = generate_boxing_pass_manager(
            enable_gates=True,
            enable_measures=True,
            inject_noise_site="after",
        )

        circuit = QuantumCircuit(3, name="GHZ with params")
        circuit.h(1)
        circuit.cx(1, 2)
        circuit.cx(1, 0)
        circuit.rz(Parameter("theta"), 0)
        circuit.rz(Parameter("phi"), 1)
        circuit.rz(Parameter("lam"), 2)
        circuit.measure_all()

        boxed_circuit = boxing_pass_manager.run(circuit)
        instructions = find_unique_box_instructions(boxed_circuit)
        assert len(instructions) == 3  # 2 with gates, 1 with measurements

        learner = NoiseLearnerV3(backend)
        learner.options.layer_pair_depths = [0, 2, 4]
        learner.options.num_randomizations = 10
        learner.options.shots_per_randomization = 100

        job = learner.run(instructions)

        result = job.result()
        assert isinstance(result, NoiseLearnerV3Results)
        assert all(isinstance(datum, NoiseLearnerV3Result) for datum in result.data)

        metadata = result[0].metadata
        assert isinstance(metadata, dict)
        assert result[0].to_pauli_lindblad_map().num_qubits == len(instructions[0].qubits)

        metadata = result[1].metadata
        assert isinstance(metadata, dict)
        assert result[1].to_pauli_lindblad_map().num_qubits == len(instructions[1].qubits)

        metadata = result[2].metadata
        assert isinstance(metadata, dict)
        assert result[2].to_pauli_lindblad_map().num_qubits == len(instructions[2].qubits)
        assert result[2].to_pauli_lindblad_map().num_terms == len(instructions[2].qubits)
