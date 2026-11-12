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

"""Tests for NoiseLearner V3."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

import pytest
from qiskit.circuit import Parameter, QuantumCircuit
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from samplomatic.transpiler import generate_boxing_pass_manager
from samplomatic.utils import find_unique_box_instructions

from qiskit_ibm_runtime import NoiseLearnerV3
from qiskit_ibm_runtime.executor_estimator import Estimator
from qiskit_ibm_runtime.results import NoiseLearnerV3Result, NoiseLearnerV3Results

from .test_executor_estimator import estimator_pubs

if TYPE_CHECKING:
    from .dependencies import Dependencies


class TestNoiseLearnerV3:
    """Test NLV3."""

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
        circuit.h(0)
        circuit.cx(0, 1)
        circuit.cx(1, 2)
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

        params = job.inputs
        # default option of experimental is Unset, and is then converted to {}
        params["options"].experimental = {}

        assert params["instructions"] == instructions
        assert params["options"] == learner.options

        result = job.result()
        assert isinstance(result, NoiseLearnerV3Results)
        assert all(isinstance(datum, NoiseLearnerV3Result) for datum in result.data)

        metadata = result[0].metadata
        assert isinstance(metadata, dict)
        assert metadata["learning_protocol"] == "lindblad"
        assert result[0].to_pauli_lindblad_map().num_qubits == len(instructions[0].qubits)

        metadata = result[1].metadata
        assert isinstance(metadata, dict)
        assert metadata["learning_protocol"] == "lindblad"
        assert result[1].to_pauli_lindblad_map().num_qubits == len(instructions[1].qubits)

        metadata = result[2].metadata
        assert isinstance(metadata, dict)
        assert metadata["learning_protocol"] == "trex"
        assert result[2].to_pauli_lindblad_map().num_qubits == len(instructions[2].qubits)
        assert result[2].to_pauli_lindblad_map().num_terms == len(instructions[2].qubits)

    @pytest.mark.parametrize("mitigation", ["pec", "pea"])
    def test_noise_learner_v3_with_estimator_layers(
        self, mitigation: Literal["pec", "pea"], dependencies: Dependencies
    ) -> None:
        """Test server-side NLV3 with unique layers from Estimator with PEC/PEA and TREX enabled."""
        backend = dependencies.service.backend(dependencies.qpu)
        pubs = estimator_pubs(backend)

        estimator = Estimator(backend)
        if mitigation == "pec":
            estimator.options.resilience.pec_mitigation = True
        else:
            estimator.options.resilience.zne_mitigation = True
            estimator.options.resilience.zne.amplifier = "pea"
        estimator.options.resilience.measure_mitigation = True

        layers = estimator.find_unique_layers(pubs, types="all")
        assert len(layers) > 0

        learner = NoiseLearnerV3(backend)
        learner.options.layer_pair_depths = [0, 2, 4]
        learner.options.num_randomizations = 10
        learner.options.shots_per_randomization = 100

        job = learner.run(layers)

        params = job.inputs
        params["options"].experimental = {}

        assert params["instructions"] == layers
        assert params["options"] == learner.options

        result = job.result()
        assert isinstance(result, NoiseLearnerV3Results)
        assert len(result) == len(layers)
        assert all(isinstance(datum, NoiseLearnerV3Result) for datum in result.data)

        has_trex = False
        has_lindblad = False
        for layer, datum in zip(layers, result.data):
            metadata = datum.metadata
            assert isinstance(metadata, dict)
            protocol = metadata["learning_protocol"]
            if protocol == "trex":
                has_trex = True
                assert datum.to_pauli_lindblad_map().num_qubits == len(layer.qubits)
                assert datum.to_pauli_lindblad_map().num_terms == len(layer.qubits)
            elif protocol == "lindblad":
                has_lindblad = True
                assert datum.to_pauli_lindblad_map().num_qubits == len(layer.qubits)

        assert has_trex
        assert has_lindblad
