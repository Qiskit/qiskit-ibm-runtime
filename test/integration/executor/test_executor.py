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

"""Tests for Executor."""

import numpy as np

from qiskit import QuantumCircuit
from qiskit.circuit import Parameter
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

from samplomatic import build
from samplomatic.transpiler import generate_boxing_pass_manager

from qiskit_ibm_runtime import Executor, QuantumProgram
from qiskit_ibm_runtime.quantum_program import QuantumProgramResult
from ...ibm_test_case import IBMIntegrationTestCase


class TestExecutor(IBMIntegrationTestCase):
    """Test Executor."""

    def setUp(self):
        """Test level setup."""
        super().setUp()
        self.backend = (backend := self.service.backend(self.dependencies.qpu))

        self.pm = generate_preset_pass_manager(backend=backend, optimization_level=0)

        self.boxing_pm = generate_preset_pass_manager(backend=backend, optimization_level=0)
        self.boxing_pm.post_scheduling = generate_boxing_pass_manager(
            enable_gates=True,
            enable_measures=True,
        )

    def test_executor_with_circuit_item(self):
        """Test sampler with a single circuit item."""
        circuit = QuantumCircuit(3, name="GHZ with params")
        circuit.h(0)
        circuit.cx(0, 1)
        circuit.cx(1, 2)
        circuit.rz(Parameter("theta"), 0)
        circuit.rz(Parameter("phi"), 1)
        circuit.rz(Parameter("lam"), 2)
        circuit.measure_all()

        shape = (2, 3)
        circuit_arguments = np.random.random(shape + (circuit.num_parameters,))

        pm = generate_preset_pass_manager(backend=self.backend, optimization_level=0)
        isa_circuit = pm.run(circuit)

        passthrough_data = {"key": "value"}
        program = QuantumProgram(shots := 123, passthrough_data=passthrough_data)
        program.append_circuit_item(isa_circuit, circuit_arguments=circuit_arguments)

        executor = Executor(self.backend)
        job = executor.run(program)

        params = job.inputs
        assert params["options"] == executor.options
        assert isinstance(params["quantum_program"], QuantumProgram)

        results = job.result()
        self.assertIsInstance(results, QuantumProgramResult)
        self.assertEqual(len(results), 1)
        self.assertEqual(results.passthrough_data, passthrough_data)

        result = results[0]
        self.assertIsInstance(result, dict)
        self.assertEqual(list(result.keys()), ["meas"])
        self.assertIsInstance(result["meas"], np.ndarray)
        self.assertEqual(result["meas"].shape, shape + (shots, circuit.num_qubits))

    def test_executor_with_samplex_item(self):
        """Test sampler with a single samplex item."""
        circuit = QuantumCircuit(3, name="GHZ with params")
        circuit.h(0)
        circuit.cx(0, 1)
        circuit.cx(1, 2)
        circuit.rz(Parameter("theta"), 0)
        circuit.rz(Parameter("phi"), 1)
        circuit.rz(Parameter("lam"), 2)
        circuit.measure_all()

        shape = (2, 3)
        parameter_values = np.random.random(shape + (circuit.num_parameters,))

        pm = generate_preset_pass_manager(backend=self.backend, optimization_level=0)
        pm.post_scheduling = generate_boxing_pass_manager(
            enable_gates=True,
            enable_measures=True,
        )
        boxed_isa_circuit = pm.run(circuit)

        isa_template, samplex = build(boxed_isa_circuit)

        passthrough_data = {"key": "value"}
        program = QuantumProgram(shots := 123, passthrough_data=passthrough_data)
        program.append_samplex_item(
            isa_template, samplex=samplex, samplex_arguments={"parameter_values": parameter_values}
        )

        executor = Executor(self.backend)
        job = executor.run(program)

        params = job.inputs
        assert params["options"] == executor.options
        assert isinstance(params["quantum_program"], QuantumProgram)

        results = job.result()
        self.assertIsInstance(results, QuantumProgramResult)
        self.assertEqual(len(results), 1)
        self.assertEqual(results.passthrough_data, passthrough_data)

        result = results[0]
        self.assertIsInstance(result, dict)
        self.assertEqual(len(result.keys()), 2)
        self.assertEqual(set(result.keys()), {"meas", "measurement_flips.meas"})
        self.assertIsInstance(result["meas"], np.ndarray)
        self.assertIsInstance(result["measurement_flips.meas"], np.ndarray)
        self.assertEqual(result["meas"].shape, shape + (shots, circuit.num_qubits))
        self.assertEqual(result["measurement_flips.meas"].shape, shape + (1, circuit.num_qubits))
