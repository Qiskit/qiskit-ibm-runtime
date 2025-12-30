# This code is part of Qiskit.
#
# (C) Copyright IBM 2025.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Tests the quantum program converters."""

import numpy as np

from samplomatic import Twirl, InjectNoise, build

from qiskit.circuit import QuantumCircuit, Parameter
from qiskit.quantum_info import PauliLindbladMap

from qiskit_ibm_runtime.quantum_program import QuantumProgram
from qiskit_ibm_runtime.quantum_program.converters import quantum_program_to_0_1
from qiskit_ibm_runtime.options.executor_options import ExecutorOptions, ExecutionOptions

from ...ibm_test_case import IBMTestCase


class TestQuantumProgramConverters(IBMTestCase):
    """Tests the quantum program converters."""
    def test_quantum_program_to_0_1(self):
        """Test the function quantum_program_to_0_1"""
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
        quantum_program.append(circuit1, circuit_arguments=circuit_arguments, chunk_size=6)

        circuit2 = QuantumCircuit(2)
        with circuit2.box(annotations=[Twirl(), InjectNoise(ref="pl0")]):
            circuit2.rx(Parameter("p"), 0)
            circuit2.cx(0, 1)
        with circuit2.box(annotations=[Twirl(), InjectNoise(ref="pl1")]):
            circuit2.measure_all()

        template_circuit, samplex = build(circuit2)
        parameter_values = np.array([[[1], [2]], [[3], [4]], [[5], [6]]])
        quantum_program.append(
            template_circuit,
            samplex=samplex,
            samplex_arguments={"parameter_values": parameter_values},
            shape=(4, 3, 2),
            chunk_size=7,
        )

        options = ExecutorOptions(execution=ExecutionOptions(init_qubits=False))

        params_model = quantum_program_to_0_1(quantum_program, options)

        self.assertEqual(params_model.schema_version, "v0.1")
        self.assertEqual(params_model.options.init_qubits, False)
        self.assertEqual(params_model.options.rep_delay, None)

        quantum_program_model = params_model.quantum_program
        self.assertEqual(quantum_program_model.shots, shots)

        circuit_item_model = quantum_program_model.items[0]
        self.assertEqual(circuit_item_model.item_type, "circuit")
        self.assertEqual(circuit_item_model.circuit.to_quantum_circuit(), circuit1)
        self.assertTrue(np.array_equal(circuit_item_model.circuit_arguments.to_numpy(), circuit_arguments))
        self.assertEqual(circuit_item_model.chunk_size, 6)