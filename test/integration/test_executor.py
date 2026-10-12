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
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from samplomatic import build
from samplomatic.transpiler import generate_boxing_pass_manager

from qiskit_ibm_runtime import Executor, QuantumProgram
from qiskit_ibm_runtime.results import QuantumProgramItemResult, QuantumProgramResult

from ..utils import make_mirror_circuit_with_phases
from .case import IBMIntegrationTestCase


class TestExecutor(IBMIntegrationTestCase):
    """Test Executor."""

    def test_executor_with_circuit_item(self):
        """Test sampler with a single circuit item."""
        backend = self.service.backend(self.dependencies.qpu)
        circuit = make_mirror_circuit_with_phases(backend, num_qubits=3)

        shape = (2, 3)
        circuit_arguments = np.random.random(shape + (circuit.num_parameters,))

        pass_manager = generate_preset_pass_manager(backend=backend, optimization_level=0)
        isa_circuit = pass_manager.run(circuit)

        passthrough_data = {
            "str": "ciao",
            "float": 1.2,
            "int": 1,
            "bool": True,
            "none": None,
            "list": [1, 2, 3],
            "array": np.array([1.0, 2.0]),
            "nested": {"array2": np.array([3.0, 4.0])},
        }
        program = QuantumProgram(shots := 123, passthrough_data=passthrough_data)
        program.append_circuit_item(isa_circuit, circuit_arguments=circuit_arguments)

        executor = Executor(backend)
        job = executor.run(program)

        params = job.inputs
        assert params["options"] == executor.options
        assert isinstance(params["quantum_program"], QuantumProgram)
        assert params["schema_version"] == Executor._SCHEMA_VERSION

        results = job.result()
        assert isinstance(results, QuantumProgramResult)
        assert len(results) == 1

        result = results[0]
        assert isinstance(result, QuantumProgramItemResult)
        assert list(result.keys()) == ["meas"]
        assert isinstance(result["meas"], np.ndarray)
        assert result["meas"].shape == shape + (shots, circuit.num_qubits)

        assert passthrough_data.keys() == results.passthrough_data.keys()
        for key in ["str", "float", "int", "bool", "none", "list"]:
            assert passthrough_data[key] == results.passthrough_data[key]
        assert isinstance(results.passthrough_data["array"], np.ndarray)
        np.testing.assert_array_equal(passthrough_data["array"], results.passthrough_data["array"])

    def test_executor_with_samplex_item(self):
        """Test sampler with a single samplex item."""
        backend = self.service.backend(self.dependencies.qpu)
        circuit = make_mirror_circuit_with_phases(backend, num_qubits=3)

        shape = (2, 3)
        parameter_values = np.random.random(shape + (circuit.num_parameters,))

        boxing_pass_manager = generate_preset_pass_manager(backend=backend, optimization_level=0)
        boxing_pass_manager.post_scheduling = generate_boxing_pass_manager(
            enable_gates=True,
            enable_measures=True,
            inject_noise_site="after",
        )
        boxed_isa_circuit = boxing_pass_manager.run(circuit)

        isa_template, samplex = build(boxed_isa_circuit)

        passthrough_data = {"key": "value"}
        program = QuantumProgram(shots := 123, passthrough_data=passthrough_data)
        program.append_samplex_item(
            isa_template, samplex=samplex, samplex_arguments={"parameter_values": parameter_values}
        )

        executor = Executor(backend)
        job = executor.run(program)

        params = job.inputs
        assert params["options"] == executor.options
        assert isinstance(params["quantum_program"], QuantumProgram)
        assert params["schema_version"] == Executor._SCHEMA_VERSION

        results = job.result()
        assert isinstance(results, QuantumProgramResult)
        assert len(results) == 1
        assert results.passthrough_data == passthrough_data

        result = results[0]
        assert isinstance(result, QuantumProgramItemResult)
        assert len(result.keys()) == 2
        assert set(result.keys()) == {"meas", "measurement_flips.meas"}
        assert isinstance(result["meas"], np.ndarray)
        assert isinstance(result["measurement_flips.meas"], np.ndarray)
        assert result["meas"].shape == shape + (shots, circuit.num_qubits)
        assert result["measurement_flips.meas"].shape == shape + (1, circuit.num_qubits)
