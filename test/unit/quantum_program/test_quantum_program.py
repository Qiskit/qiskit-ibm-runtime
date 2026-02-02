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

"""Tests the class `QuantumProgram`."""

import numpy as np

from samplomatic import Twirl, InjectNoise, build

from qiskit.circuit import QuantumCircuit, Parameter
from qiskit.quantum_info import PauliLindbladMap

from qiskit_ibm_runtime.quantum_program import QuantumProgram

from ...ibm_test_case import IBMTestCase


class TestQuantumProgram(IBMTestCase):
    """Tests the ``QuantumProgram`` class."""

    def test_quantum_program(self):
        """Test a quantum program consisting of a circuit item and a samplex item."""
        shots = 100

        noise_models = [
            PauliLindbladMap.from_list([("IX", 0.04), ("XX", 0.05)]),
            PauliLindbladMap.from_list([("XI", 0.02), ("IZ", 0.035)]),
        ]

        quantum_program = QuantumProgram(
            shots=shots,
            noise_maps={f"pl{i}": noise_model for i, noise_model in enumerate(noise_models)},
        )

        circuit1 = QuantumCircuit(1)
        circuit1.rx(Parameter("p"), 0)

        circuit_arguments = np.array([[3], [4], [5]])
        quantum_program.append_circuit_item(
            circuit1, circuit_arguments=circuit_arguments, chunk_size=6
        )

        circuit2 = QuantumCircuit(2)
        with circuit2.box(annotations=[Twirl(), InjectNoise(ref="pl0")]):
            circuit2.rx(Parameter("p"), 0)
            circuit2.cx(0, 1)
        with circuit2.box(annotations=[Twirl(), InjectNoise(ref="pl1")]):
            circuit2.measure_all()

        template_circuit, samplex = build(circuit2)
        parameter_values = np.array([[[1], [2]], [[3], [4]], [[5], [6]]])
        quantum_program.append_samplex_item(
            template_circuit,
            samplex=samplex,
            samplex_arguments={"parameter_values": parameter_values},
            shape=(4, 3, 2),
            chunk_size=7,
        )

        new_noise_models = [
            PauliLindbladMap.from_list([("YI", 0.03), ("IY", 0.01)]),
            PauliLindbladMap.from_list([("ZI", 0.025), ("XZ", 0.045)]),
        ]
        quantum_program.append_samplex_item(
            template_circuit,
            samplex=samplex,
            samplex_arguments={
                "parameter_values": parameter_values,
                "pauli_lindblad_maps": {
                    f"pl{i}": noise_model for i, noise_model in enumerate(new_noise_models)
                },
            },
        )

        self.assertEqual(quantum_program.shots, shots)

        circuit_item = quantum_program.items[0]
        self.assertEqual(circuit_item.circuit, circuit1)
        self.assertTrue(np.array_equal(circuit_item.circuit_arguments, circuit_arguments))
        self.assertEqual(circuit_item.chunk_size, 6)
        self.assertEqual(circuit_item.shape, (3,))

        samplex_item = quantum_program.items[1]
        self.assertEqual(samplex_item.samplex, samplex)
        self.assertEqual(samplex_item.circuit, template_circuit)
        self.assertEqual(samplex_item.chunk_size, 7)
        self.assertEqual(samplex_item.shape, (4, 3, 2))
        self.assertTrue(
            np.array_equal(samplex_item.samplex_arguments["parameter_values"], parameter_values)
        )
        for i, noise_model in enumerate(noise_models):
            self.assertEqual(
                samplex_item.samplex_arguments[f"pauli_lindblad_maps.pl{i}"], noise_model
            )

        samplex_item_with_new_noise = quantum_program.items[2]
        for i, noise_model in enumerate(new_noise_models):
            self.assertEqual(
                samplex_item_with_new_noise.samplex_arguments[f"pauli_lindblad_maps.pl{i}"],
                noise_model,
            )

    def test_subset_of_noise_maps(self):
        """Test that `QuantumProgram` knows to handle the case where a specific samplex
        item uses only a subset of the program's noise maps."""
        shots = 100

        noise_models = [
            PauliLindbladMap.from_list([("IX", 0.04), ("XX", 0.05)]),
            PauliLindbladMap.from_list([("XI", 0.02), ("IZ", 0.035)]),
        ]

        quantum_program = QuantumProgram(
            shots=shots,
            noise_maps={f"pl{i}": noise_model for i, noise_model in enumerate(noise_models)},
        )

        circuit2 = QuantumCircuit(2)
        with circuit2.box(annotations=[Twirl(), InjectNoise(ref="pl1")]):
            circuit2.measure_all()

        template_circuit, samplex = build(circuit2)
        quantum_program.append_samplex_item(
            template_circuit,
            samplex=samplex,
            shape=(4, 3, 2),
            chunk_size=7,
        )

        samplex_item = quantum_program.items[0]
        self.assertEqual(samplex_item.samplex, samplex)
        self.assertEqual(samplex_item.circuit, template_circuit)
        self.assertEqual(samplex_item.chunk_size, 7)
        self.assertEqual(samplex_item.shape, (4, 3, 2))
        self.assertEqual(samplex_item.samplex_arguments["pauli_lindblad_maps.pl1"], noise_models[1])
