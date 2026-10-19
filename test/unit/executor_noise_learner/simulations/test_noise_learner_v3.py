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

"""Tests client-side noise learner implementation using simulator through local mode."""

from __future__ import annotations

from qiskit import QuantumCircuit
from qiskit.quantum_info import PauliLindbladMap
from qiskit.transpiler import generate_preset_pass_manager
from qiskit_aer import AerSimulator
from samplomatic.transpiler import generate_boxing_pass_manager
from samplomatic.utils import find_unique_box_instructions

from qiskit_ibm_runtime.executor_noise_learner import NoiseLearnerV3 as NoiseLearner
from qiskit_ibm_runtime.fake_provider import FakeManilaV2


class TestNoiseLearnerV3:
    """Tests client-side noise learner using simulator with noise through local mode."""

    def test_noise_learning_with_identity_noise_injection(self) -> None:
        """Tests the client-side noise learner with local mode noise injection.

        The resulting noise model should match what is injected.
        """
        backend = AerSimulator(method="stabilizer", target=FakeManilaV2().target)

        circuit = QuantumCircuit(2)
        circuit.cz(0, 1)
        circuit.measure_all()

        pass_manager = generate_preset_pass_manager(optimization_level=0, backend=backend)
        pass_manager.post_scheduling = generate_boxing_pass_manager(add_tags="unique_box")
        boxed_circuit = pass_manager.run(circuit)

        layers = find_unique_box_instructions(boxed_circuit.data)
        noise_maps = [
            PauliLindbladMap.identity(layers[0].operation.num_qubits),
            PauliLindbladMap.identity(layers[1].operation.num_qubits),
        ]

        noise_learner = NoiseLearner(mode=backend)
        noise_learner.options.simulator.layer_noise_model = list(zip(layers, noise_maps))
        noise_learner.options.shots_per_randomization = 256
        job = noise_learner.run(layers)
        result = job.result()

        simplified_noise_maps = [
            noise_map.simplify() for noise_map in result.to_pauli_lindblad_maps()
        ]
        assert simplified_noise_maps == noise_maps
