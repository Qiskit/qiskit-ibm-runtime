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

from qiskit.circuit import Parameter, QuantumCircuit
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

from samplomatic.transpiler import generate_boxing_pass_manager
from samplomatic.utils import find_unique_box_instructions

from qiskit_ibm_runtime import NoiseLearnerV3
from qiskit_ibm_runtime.results import NoiseLearnerV3Results, NoiseLearnerV3Result
from ..ibm_test_case import IBMIntegrationTestCase


class TestNoiseLearnerV3(IBMIntegrationTestCase):
    """Test NLV3."""

    def setUp(self):
        """Test level setup."""
        super().setUp()
        self.backend = (backend := self.service.backend(self.dependencies.qpu))

        self.boxing_pm = generate_preset_pass_manager(backend=backend, optimization_level=0)
        self.boxing_pm.post_scheduling = generate_boxing_pass_manager(
            enable_gates=True,
            enable_measures=True,
        )

    def test_noise_learner_v3(self):
        """Test NLV3 with basic options."""
        circuit = QuantumCircuit(3, name="GHZ with params")
        circuit.h(0)
        circuit.cx(0, 1)
        circuit.cx(1, 2)
        circuit.rz(Parameter("theta"), 0)
        circuit.rz(Parameter("phi"), 1)
        circuit.rz(Parameter("lam"), 2)
        circuit.measure_all()

        boxed_circuit = self.boxing_pm.run(circuit)
        instructions = find_unique_box_instructions(boxed_circuit)
        assert len(instructions) == 3  # 2 with gates, 1 with measurements

        learner = NoiseLearnerV3(self.backend)
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
        assert all(isinstance(datum, NoiseLearnerV3Result) for datum in result)

        assert result[0].metadata["learning_protocol"] == "lindblad"
        assert result[0].to_pauli_lindblad_map().num_qubits == len(instructions[0].qubits)

        assert result[1].metadata["learning_protocol"] == "lindblad"
        assert result[1].to_pauli_lindblad_map().num_qubits == len(instructions[1].qubits)

        assert result[2].metadata["learning_protocol"] == "trex"
        assert result[2].to_pauli_lindblad_map().num_qubits == len(instructions[2].qubits)
        assert result[2].to_pauli_lindblad_map().num_terms == len(instructions[2].qubits)
