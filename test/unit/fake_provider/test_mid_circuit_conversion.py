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

"""Test the conversion of mid-circuit instructions to standard ones for simulation."""

from __future__ import annotations

import pytest
from qiskit.circuit import Instruction, Measure, QuantumCircuit, Reset
from qiskit.providers.fake_provider import GenericBackendV2
from qiskit.transpiler import generate_preset_pass_manager

from qiskit_ibm_runtime.circuit import MeasureReset, MidCircuitMeasure, MidCircuitReset
from qiskit_ibm_runtime.fake_provider.mid_circuit_conversion import convert_mid_circuit_instructions


class TestConvertMidCircuitInstructions:
    """Test the convert_mid_circuit_instructions function."""

    @pytest.mark.parametrize(
        ("instruction", "expected"),
        [
            (MidCircuitMeasure(), Measure()),
            (MidCircuitMeasure("measure_3"), Measure()),
            (MidCircuitReset(), Reset()),
            (MidCircuitReset("reset_3"), Reset()),
        ],
    )
    def test_convert(self, instruction: Instruction, expected: Instruction) -> None:
        """Test that mid-circuit instructions are replaced by their standard counterparts."""
        circuit = QuantumCircuit(1, 1)
        circuit.append(instruction, [0], range(instruction.num_clbits))
        expected_circuit = QuantumCircuit(1, 1)
        expected_circuit.append(expected, [0], range(expected.num_clbits))

        assert convert_mid_circuit_instructions(circuit) == expected_circuit

    @pytest.mark.parametrize(
        "instruction",
        [
            MeasureReset(),
            MidCircuitMeasure("measure_reset"),
            MidCircuitMeasure("measure_custom"),
            MidCircuitReset("reset_custom"),
            Instruction("measure_2", 2, 2, []),
            Instruction("reset_2", 2, 0, []),
            Instruction("measure_2", 1, 0, []),
            Instruction("reset_2", 1, 1, []),
        ],
    )
    def test_other_instructions_unchanged(self, instruction: Instruction) -> None:
        """Test that instructions not matching the mid-circuit signatures are not converted."""
        circuit = QuantumCircuit(2, 2)
        circuit.append(instruction, range(instruction.num_qubits), range(instruction.num_clbits))

        assert convert_mid_circuit_instructions(circuit) == circuit

    def test_convert_inside_control_flow(self) -> None:
        """Test the conversion inside nested control flow, leaving the input circuit unchanged."""
        circuit = QuantumCircuit(1, 1)
        with circuit.box():
            with circuit.if_test((circuit.clbits[0], 1)):
                circuit.append(MidCircuitMeasure(), [0], [0])
                circuit.append(MidCircuitReset(), [0])
        original = circuit.copy()
        expected = QuantumCircuit(1, 1)
        with expected.box():
            with expected.if_test((expected.clbits[0], 1)):
                expected.measure(0, 0)
                expected.reset(0)

        converted = convert_mid_circuit_instructions(circuit)

        assert converted == expected
        assert circuit == original

    def test_preserves_circuit_attributes(self) -> None:
        """Test that the converted circuit keeps the attributes of the input."""
        pass_manager = generate_preset_pass_manager(
            optimization_level=0, backend=GenericBackendV2(num_qubits=5, seed=0), initial_layout=[3]
        )
        circuit = pass_manager.run(QuantumCircuit(1, 1, name="circ", metadata={"key": "value"}))
        circuit.append(MidCircuitMeasure(), [3], [0])
        circuit.global_phase = 0.5
        assert circuit.layout is not None

        converted = convert_mid_circuit_instructions(circuit)

        assert converted.count_ops() == {"measure": 1}
        assert converted.name == circuit.name
        assert converted.metadata == circuit.metadata
        assert converted.global_phase == circuit.global_phase
        assert converted.layout == circuit.layout
