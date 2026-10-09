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

from ddt import data, ddt, unpack
from qiskit.circuit import Instruction, QuantumCircuit
from qiskit.providers.fake_provider import GenericBackendV2
from qiskit.transpiler import PassManager, generate_preset_pass_manager

from qiskit_ibm_runtime.circuit import MeasureReset, MidCircuitMeasure, MidCircuitReset
from qiskit_ibm_runtime.fake_provider.mid_circuit_conversion import (
    ConvertMidCircuitToStandard,
    convert_mid_circuit_instructions,
)

from ...ibm_test_case import IBMTestCase


def build_circuit(add_operations, control_flow=None):
    """Return a 1-qubit, 1-clbit circuit with ``add_operations`` applied inside ``control_flow``."""
    circuit = QuantumCircuit(1, 1)
    if control_flow is None:
        add_operations(circuit)
    elif control_flow == "if_test":
        with circuit.if_test((circuit.clbits[0], 1)):
            add_operations(circuit)
    elif control_flow == "while_loop":
        with circuit.while_loop((circuit.clbits[0], 0)):
            add_operations(circuit)
    elif control_flow == "for_loop":
        with circuit.for_loop(range(2)):
            add_operations(circuit)
    elif control_flow == "box":
        with circuit.box():
            add_operations(circuit)
    return circuit


def add_mid_circuit_operations(circuit):
    """Append a mid-circuit measure and a mid-circuit reset."""
    circuit.append(MidCircuitMeasure(), [0], [0])
    circuit.append(MidCircuitReset(), [0])


def add_standard_operations(circuit):
    """Append the standard counterparts of ``add_mid_circuit_operations``."""
    circuit.measure(0, 0)
    circuit.reset(0)


@ddt
class TestConvertMidCircuitToStandard(IBMTestCase):
    """Test the ConvertMidCircuitToStandard pass."""

    @data(
        (MidCircuitMeasure(), lambda circuit: circuit.measure(0, 0)),
        (MidCircuitMeasure("measure_3"), lambda circuit: circuit.measure(0, 0)),
        (MidCircuitReset(), lambda circuit: circuit.reset(0)),
        (MidCircuitReset("reset_3"), lambda circuit: circuit.reset(0)),
    )
    @unpack
    def test_convert(self, instruction, add_expected):
        """Test that mid-circuit instructions are replaced by their standard counterparts."""
        circuit = QuantumCircuit(1, 1)
        circuit.append(instruction, [0], [0] if instruction.num_clbits else [])

        converted = PassManager([ConvertMidCircuitToStandard()]).run(circuit)

        self.assertEqual(converted, build_circuit(add_expected))

    @data("if_test", "while_loop", "for_loop", "box")
    def test_convert_inside_control_flow(self, control_flow):
        """Test that mid-circuit instructions inside control-flow blocks are replaced."""
        circuit = build_circuit(add_mid_circuit_operations, control_flow)

        converted = PassManager([ConvertMidCircuitToStandard()]).run(circuit)

        self.assertEqual(converted, build_circuit(add_standard_operations, control_flow))

    @data(
        MeasureReset(),
        MidCircuitMeasure("measure_reset"),
        MidCircuitMeasure("measure_custom"),
        MidCircuitReset("reset_custom"),
        Instruction("measure_2", 2, 2, []),
        Instruction("reset_2", 2, 0, []),
        Instruction("measure_2", 1, 0, []),
        Instruction("reset_2", 1, 1, []),
    )
    def test_other_instructions_unchanged(self, instruction):
        """Test that instructions not matching the mid-circuit signatures are not converted."""
        circuit = QuantumCircuit(2, 2)
        circuit.append(instruction, range(instruction.num_qubits), range(instruction.num_clbits))

        converted = PassManager([ConvertMidCircuitToStandard()]).run(circuit)

        self.assertEqual(converted, circuit)


@ddt
class TestConvertMidCircuitInstructions(IBMTestCase):
    """Test the convert_mid_circuit_instructions function."""

    @data(
        add_standard_operations,
        lambda circuit: circuit.append(MeasureReset(), [0], [0]),
        lambda circuit: circuit.append(MidCircuitMeasure("measure_custom"), [0], [0]),
        lambda circuit: circuit.append(Instruction("measure_2", 1, 0, []), [0]),
    )
    def test_returns_same_circuit_without_mid_circuit_instructions(self, add_operations):
        """Test that circuits without instructions to convert are returned as they are."""
        circuit = build_circuit(add_operations)

        self.assertIs(convert_mid_circuit_instructions(circuit), circuit)

    @data(None, "if_test")
    def test_converts_without_modifying_input(self, control_flow):
        """Test that the converted circuit is a copy and the input circuit is unchanged."""
        circuit = build_circuit(add_mid_circuit_operations, control_flow)
        original = circuit.copy()

        converted = convert_mid_circuit_instructions(circuit)

        self.assertEqual(converted, build_circuit(add_standard_operations, control_flow))
        self.assertEqual(circuit, original)

    def test_preserves_circuit_attributes(self):
        """Test that the converted circuit keeps the attributes of the input."""
        pass_manager = generate_preset_pass_manager(
            optimization_level=0, backend=GenericBackendV2(num_qubits=5, seed=0), initial_layout=[3]
        )
        circuit = pass_manager.run(QuantumCircuit(1, 1, name="circ", metadata={"key": "value"}))
        circuit.append(MidCircuitMeasure(), [3], [0])
        circuit.global_phase = 0.5
        self.assertIsNotNone(circuit.layout)

        converted = convert_mid_circuit_instructions(circuit)

        self.assertEqual(converted.count_ops(), {"measure": 1})
        self.assertEqual(converted.name, circuit.name)
        self.assertEqual(converted.metadata, circuit.metadata)
        self.assertEqual(converted.global_phase, circuit.global_phase)
        self.assertEqual(converted.layout, circuit.layout)
