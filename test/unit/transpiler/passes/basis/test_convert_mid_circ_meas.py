# This code is part of Qiskit.
#
# (C) Copyright IBM 2025-2026.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Test the conversion to mid-circuit instructions."""

from qiskit.circuit import QuantumCircuit
from qiskit.circuit.library import Measure, Reset
from qiskit.providers.fake_provider import GenericBackendV2
from qiskit.transpiler import PassManager

from qiskit_ibm_runtime.circuit import MeasureReset, MidCircuitMeasure, MidCircuitReset
from qiskit_ibm_runtime.transpiler.passes.basis.convert_mid_circ_meas import (
    ConvertToMeasureReset,
    ConvertToMidCircuitMeasure,
    ConvertToMidCircuitResetAndMeasure,
)

from .....ibm_test_case import IBMTestCase


def target_with_mid_circuit_instructions(measure_name="measure_2", reset_name="reset_2"):
    """Return a target supporting a mid-circuit measure and reset on every qubit."""
    target = GenericBackendV2(num_qubits=5, seed=0).target
    target.add_instruction(MidCircuitMeasure(measure_name), {(i,): None for i in range(5)})
    target.add_instruction(MidCircuitReset(reset_name), {(i,): None for i in range(5)})
    return target


def circuit_with_mid_circuit_instructions():
    """Return a circuit with mid-circuit measures and resets, plus terminal measures."""
    circuit = QuantumCircuit(2, 2)
    circuit.x(0)
    circuit.append(MidCircuitMeasure(), [0], [0])
    circuit.append(MidCircuitReset(), [0])
    circuit.reset(0)
    circuit.measure([0], [0])
    circuit.measure_all()
    return circuit


def target_with_measure_reset(measure_reset_name="measure_reset"):
    """Return a target supporting measure-reset on every qubit."""
    target = GenericBackendV2(num_qubits=5, seed=0).target
    target.add_instruction(MeasureReset(measure_reset_name), {(i,): None for i in range(5)})
    return target


class TestConvertToMidCircuitMeasure(IBMTestCase):
    """Tests the ConvertToMidCircuitMeasure pass."""

    def test_convert_default(self):
        """Test basic conversion to measure_2 and reset_2."""
        custom_pass = ConvertToMidCircuitResetAndMeasure(target_with_mid_circuit_instructions())
        pm = PassManager([custom_pass])
        transpiled = pm.run(circuit_with_mid_circuit_instructions())

        # The transpiled circuit will contain measure_2 in the two mid-circ-measurements
        # and regular Measure instances in terminal measurements,
        # similarly it will contain reset_2 in the two mid-circuit resets
        self.assertIsInstance(transpiled.data[1].operation, MidCircuitMeasure)
        self.assertIsInstance(transpiled.data[2].operation, MidCircuitReset)
        self.assertIsInstance(transpiled.data[3].operation, MidCircuitReset)
        self.assertIsInstance(transpiled.data[4].operation, MidCircuitMeasure)
        # [5] is the barrier
        self.assertNotIsInstance(transpiled.data[6].operation, MidCircuitMeasure)
        self.assertIsInstance(transpiled.data[6].operation, Measure)
        self.assertNotIsInstance(transpiled.data[7].operation, MidCircuitMeasure)
        self.assertIsInstance(transpiled.data[7].operation, Measure)

    def test_convert_raises(self):
        """Test that value error is raised if measure_2 not supported in target."""
        with self.assertRaisesRegex(
            ValueError,
            r"measure_2 is not supported by the given target\. "
            r"Supported operations are: dict_keys\(\['cx', 'id', 'rz', "
            r"'sx', 'x', 'reset', 'delay', 'measure'\]\)",
        ):
            ConvertToMidCircuitMeasure(GenericBackendV2(num_qubits=5, seed=0).target)

    def test_convert_measure_3(self):
        """Test conversion with non-default alternative measure and reset.

        The pass is only expected to convert the non-terminal measure into measure_3, the existing
        measure_2 instruction is left untouched.
        Similarly, it will convert the reset into reset_3, leaving the existing reset_2 untouched.
        """
        target = target_with_mid_circuit_instructions("measure_3", "reset_3")

        custom_pass = ConvertToMidCircuitResetAndMeasure(target, "measure_3", "reset_3")
        pm = PassManager([custom_pass])
        transpiled = pm.run(circuit_with_mid_circuit_instructions())

        self.assertIsInstance(transpiled.data[1].operation, MidCircuitMeasure)
        self.assertIsInstance(transpiled.data[2].operation, MidCircuitReset)
        self.assertIsInstance(transpiled.data[3].operation, MidCircuitReset)
        self.assertIsInstance(transpiled.data[4].operation, MidCircuitMeasure)
        self.assertEqual(transpiled.data[1].operation.name, "measure_2")
        self.assertEqual(transpiled.data[2].operation.name, "reset_2")
        self.assertEqual(transpiled.data[3].operation.name, "reset_3")
        self.assertEqual(transpiled.data[4].operation.name, "measure_3")
        # [5] is the barrier
        self.assertNotIsInstance(transpiled.data[6].operation, MidCircuitMeasure)
        self.assertIsInstance(transpiled.data[6].operation, Measure)
        self.assertNotIsInstance(transpiled.data[7].operation, MidCircuitMeasure)
        self.assertIsInstance(transpiled.data[7].operation, Measure)

    def test_different_qarg(self):
        """Test correct replacing of measure_2.

        Test that non-terminal measure is only replaced if measure_2 is defined
        in corresponding qarg (else, it's left untouched, and a warning is raised).
        """
        num_qubits = 5
        mcm = MidCircuitMeasure()
        mcr = MidCircuitReset()
        target = GenericBackendV2(num_qubits=num_qubits, seed=0).target
        # only define measure_2 and reset_2 in physical qubit 0
        target.add_instruction(mcm, {(0,): None})
        target.add_instruction(mcr, {(0,): None})

        qc = QuantumCircuit(3, 2)
        # place measure in qubit 1
        qc.measure([1], [1])
        qc.reset(1)
        qc.barrier()
        qc.x(0)
        qc.measure_all()

        custom_pass = ConvertToMidCircuitMeasure(target)
        pm = PassManager([custom_pass])
        with self.assertWarnsRegex(UserWarning, "'measure_2'"):
            transpiled = pm.run(qc)

        # The transpiled circuit will not contain any MidCircuitMeasure instance
        self.assertNotIsInstance(transpiled.data[0].operation, MidCircuitMeasure)
        self.assertIsInstance(transpiled.data[0].operation, Measure)
        self.assertNotIsInstance(transpiled.data[1].operation, MidCircuitReset)
        self.assertIsInstance(transpiled.data[1].operation, Reset)
        # [4] is a barrier
        self.assertNotIsInstance(transpiled.data[5].operation, MidCircuitMeasure)
        self.assertIsInstance(transpiled.data[5].operation, Measure)


class TestConvertToMeasureReset(IBMTestCase):
    """Tests the ConvertToMeasureReset pass."""

    def test_convert_default(self):
        """Test basic conversion to measure_reset."""
        custom_pass = ConvertToMeasureReset(target_with_measure_reset())
        pm = PassManager([custom_pass])

        # Measure - Reset - X, on the same qubit
        circuit = QuantumCircuit(1, 1)
        circuit.measure(0, 0)
        circuit.reset(0)
        circuit.x(0)

        transpiled = pm.run(circuit)

        # The measure-reset sequence is replaced by a single MeasureReset instruction.
        self.assertIsInstance(transpiled.data[0].operation, MeasureReset)
        self.assertEqual(transpiled.data[1].operation.name, "x")

    def test_interrupted_sequence(self):
        """Test that conversion does not occur with a gate in between."""
        custom_pass = ConvertToMeasureReset(target_with_measure_reset())
        pm = PassManager([custom_pass])

        # Measure - X - Reset, on the same qubit
        circuit = QuantumCircuit(1, 1)
        circuit.measure(0, 0)
        circuit.x(0)
        circuit.reset(0)

        transpiled = pm.run(circuit)

        # The circuit is untouched.
        self.assertIsInstance(transpiled.data[0].operation, Measure)
        self.assertEqual(transpiled.data[1].operation.name, "x")
        self.assertIsInstance(transpiled.data[2].operation, Reset)

        self.assertFalse(
            any(isinstance(instruction.operation, MeasureReset) for instruction in transpiled.data)
        )

    def test_different_qarg(self):
        """Test that measure and reset on different qubits are not converted."""
        custom_pass = ConvertToMeasureReset(target_with_measure_reset())
        pm = PassManager([custom_pass])

        # Measure on one qubit, Reset on another qubit
        circuit = QuantumCircuit(2, 1)
        circuit.measure(0, 0)
        circuit.reset(1)

        transpiled = pm.run(circuit)

        # The circuit is untouched.
        measures = [
            instruction
            for instruction in transpiled.data
            if isinstance(instruction.operation, Measure)
        ]
        resets = [
            instruction
            for instruction in transpiled.data
            if isinstance(instruction.operation, Reset)
        ]

        self.assertEqual(len(measures), 1)
        self.assertEqual(len(resets), 1)

        self.assertEqual(transpiled.find_bit(measures[0].qubits[0]).index, 0)
        self.assertEqual(transpiled.find_bit(resets[0].qubits[0]).index, 1)

        self.assertFalse(
            any(isinstance(instruction.operation, MeasureReset) for instruction in transpiled.data)
        )

    def test_unsupported_qarg(self):
        """Test that conversion only occurs on supported qargs."""
        target = GenericBackendV2(num_qubits=2, seed=0).target

        # MeasureReset is supported on qubit 0, but not on qubit 1
        target.add_instruction(MeasureReset(), {(0,): None})
        custom_pass = ConvertToMeasureReset(target)
        pm = PassManager([custom_pass])

        circuit = QuantumCircuit(2, 2)
        # Measure - Reset - X on qubit 0
        circuit.measure(0, 0)
        circuit.reset(0)
        circuit.x(0)

        # Measure - Reset - X on qubit 1
        circuit.measure(1, 1)
        circuit.reset(1)
        circuit.x(1)

        transpiled = pm.run(circuit)

        measure_resets = [
            instruction
            for instruction in transpiled.data
            if isinstance(instruction.operation, MeasureReset)
        ]
        measures = [
            instruction
            for instruction in transpiled.data
            if isinstance(instruction.operation, Measure)
        ]
        resets = [
            instruction
            for instruction in transpiled.data
            if isinstance(instruction.operation, Reset)
        ]
        xs = [instruction for instruction in transpiled.data if instruction.operation.name == "x"]

        # Only one sequence Measure-Reset got converted
        self.assertEqual(len(measure_resets), 1)
        self.assertEqual(len(measures), 1)
        self.assertEqual(len(resets), 1)
        # The two Xs were untouched
        self.assertEqual(len(xs), 2)

        # The MeasureReset is on qubit 0
        self.assertEqual(transpiled.find_bit(measure_resets[0].qubits[0]).index, 0)

        # The Measure and Reset are still on qubit 1
        self.assertEqual(transpiled.find_bit(measures[0].qubits[0]).index, 1)
        self.assertEqual(transpiled.find_bit(resets[0].qubits[0]).index, 1)
