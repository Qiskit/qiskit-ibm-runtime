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

import numpy as np
import pytest
from qiskit import QuantumCircuit
from qiskit.quantum_info import PauliLindbladMap, random_pauli_list
from qiskit.transpiler import generate_preset_pass_manager
from qiskit_aer import AerSimulator
from samplomatic import InjectNoise, Tag, Twirl
from samplomatic.transpiler import generate_boxing_pass_manager
from samplomatic.utils import find_unique_box_instructions

from qiskit_ibm_runtime.executor_noise_learner import NoiseLearnerV3 as NoiseLearner
from qiskit_ibm_runtime.utils.utils import HAS_QNL


def compare_pauli_lindblad_maps(
    actual: PauliLindbladMap, desired: PauliLindbladMap, atol: float = 0.005
) -> None:
    """Compare ``actual`` to ``desired`` via their rates.

    The two maps are considered equal if every (approximately) non-zero rate in
    ``actual`` matches the corresponding rate in ``desired`` and
    ``actual`` is not missing any (approximately) non-zero term that appears in
    ``desired``.

    Args:
        actual: The ``PauliLindbladMap`` to test.
        desired: The ``PauliLindbladMap`` to compare against.
        atol: Absolute tolerance used when comparing rates.

    Raises:
        AssertionError: If ``actual`` and ``desired`` are not equal within ``atol``.
    """
    desired_table: dict[str, dict] = {}
    for gen, qubits, rate in desired.to_sparse_list():
        desired_table.setdefault(gen, {})[tuple(qubits)] = rate

    for gen, qubits, rate in actual.to_sparse_list():
        if gen in desired_table and tuple(qubits) in desired_table[gen]:
            np.testing.assert_allclose(desired_table[gen][tuple(qubits)], rate, atol=atol)
            desired_table[gen].pop(tuple(qubits))
        else:
            np.testing.assert_allclose(rate, 0, atol=atol)
    remaining_rates = [
        rate for qubit_rates in desired_table.values() for rate in qubit_rates.values()
    ]
    np.testing.assert_allclose(remaining_rates, 0, atol=atol)


def generate_random_pauli_lindblad_map(
    num_qubits: int, size: int = 1, max_rate: float = 1.0, seed: int | None = None
) -> PauliLindbladMap:
    """Generates a random ``PauliLindbladMap``.

    Args:
        num_qubits: The number of qubits.
        size: The number of Pauli terms.
        max_rate: The maximum allowable rate.
        seed: Set a fixed seed or generator for RNG.

    Returns:
        A random ``PauliLindbladMap``.
    """
    rng = np.random.default_rng(seed)
    generators = random_pauli_list(num_qubits, size=size, seed=rng, phase=False)
    return PauliLindbladMap.from_list([(str(gen), rng.uniform(0, max_rate)) for gen in generators])


@pytest.mark.skipif(not HAS_QNL, reason="qiskit-noise-learning is required to run this test")
class TestNoiseLearnerV3:
    """Tests client-side noise learner using simulator with noise through local mode."""

    def test_noise_learning_with_noise_injection(self) -> None:
        """Tests the client-side noise learner with local mode noise injection.

        The resulting noise model should match what is injected.
        """
        backend = AerSimulator(method="stabilizer")
        backend.set_max_qubits(2)

        circuit = QuantumCircuit(2)
        circuit.cz(0, 1)
        circuit.measure_all()

        pass_manager = generate_preset_pass_manager(optimization_level=0, backend=backend)
        pass_manager.post_scheduling = generate_boxing_pass_manager(add_tags="unique_box")
        boxed_circuit = pass_manager.run(circuit)

        layers = find_unique_box_instructions(boxed_circuit.data)

        noise_maps = [
            PauliLindbladMap.from_list([("ZI", 0.03), ("XI", 0.04)]),
            PauliLindbladMap.from_list([("XI", 0.02), ("IX", 0.01)]),
        ]

        noise_learner = NoiseLearner(mode=backend)
        noise_learner.options.simulator.layer_noise_model = list(zip(layers, noise_maps))
        job = noise_learner.run(layers)
        result = job.result()

        simplified_noise_maps = [
            noise_map.simplify() for noise_map in result.to_pauli_lindblad_maps()
        ]

        # expect a degeneracy with the noncommutative "XI" term
        expected_gate_map = PauliLindbladMap.from_list(
            [
                ("XZ", 0.04 / 2),
                ("XI", 0.04 / 2),
                ("ZI", 0.03),
            ]
        )
        compare_pauli_lindblad_maps(simplified_noise_maps[0], expected_gate_map)
        compare_pauli_lindblad_maps(simplified_noise_maps[1], noise_maps[1], atol=6e-3)

    @pytest.mark.parametrize("qubits", [(0, 1), (1, 0), (3, 4, 2)])
    def test_noise_learning_with_noop_noise_injection(self, qubits):
        """Tests the client-side noise learner with local mode noise injection and a noop layer.

        The resulting noise model should match what is injected.
        """
        backend = AerSimulator(method="stabilizer")
        backend.set_max_qubits(5)

        circuit = QuantumCircuit(backend.num_qubits)
        with circuit.box(annotations=[Twirl(), InjectNoise("my_ref"), Tag()]):
            circuit.noop(qubits)

        layers = find_unique_box_instructions(circuit.data)
        noise_maps = [
            generate_random_pauli_lindblad_map(
                num_qubits=layer.operation.num_qubits, size=10, max_rate=0.003
            )
            for layer in layers
        ]

        noise_learner = NoiseLearner(mode=backend)
        noise_learner.options.simulator.layer_noise_model = zip(layers, noise_maps)
        noise_learner.options.simulator.warn_absent = False  # due to missing `M` tag
        job = noise_learner.run(layers)
        result = job.result()

        simplified_noise_maps = [
            noise_map.simplify() for noise_map in result.to_pauli_lindblad_maps()
        ]

        for obtained, expected in zip(simplified_noise_maps, noise_maps):
            compare_pauli_lindblad_maps(obtained, expected)

    @pytest.mark.parametrize("qubits", [(0, 1), (1, 0), (3, 4, 2)])
    def test_noise_learning_with_meas_noise_injection(self, qubits):
        """Tests the client-side noise learner with local mode noise injection and a meas layer.

        The resulting noise model should match what is injected.
        """
        backend = AerSimulator(method="stabilizer")
        backend.set_max_qubits(num_qubits := max(qubits) + 1)

        circuit = QuantumCircuit(num_qubits, num_qubits)
        with circuit.box(annotations=[Twirl(), InjectNoise("my_ref"), Tag()]):
            circuit.measure(qubits, qubits)

        layers = find_unique_box_instructions(circuit.data)
        noise_maps = [
            generate_random_pauli_lindblad_map(
                num_qubits=layer.operation.num_qubits, size=10, max_rate=0.003
            )
            for layer in layers
        ]

        noise_learner = NoiseLearner(mode=backend)
        noise_learner.options.simulator.layer_noise_model = zip(layers, noise_maps)
        job = noise_learner.run(layers)
        result = job.result()

        simplified_noise_maps = [
            noise_map.simplify() for noise_map in result.to_pauli_lindblad_maps()
        ]

        for obtained, expected in zip(simplified_noise_maps, noise_maps):
            compare_pauli_lindblad_maps(obtained, expected)
