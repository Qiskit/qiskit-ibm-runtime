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

"""Test the conversion of terminal Measure to MidCircuitMeasure."""

import warnings

from ddt import data, ddt
from qiskit.circuit import ClassicalRegister, IfElseOp, QuantumCircuit, QuantumRegister
from qiskit.circuit.classical import expr
from qiskit.circuit.library import Measure, Reset, XGate
from qiskit.providers.fake_provider import GenericBackendV2
from qiskit.transpiler import PassManager
from qiskit.transpiler.passes import ResetAfterMeasureSimplification

from qiskit_ibm_runtime.circuit import MeasureReset, MidCircuitMeasure, MidCircuitReset
from qiskit_ibm_runtime.transpiler.passes.basis.convert_mid_circ_meas import (
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


def target_with_measure_reset(measure_reset_name="measure_reset", qubits=range(5)):
    """Return a target supporting mid-circuit instructions, and measure-reset on ``qubits``."""
    target = target_with_mid_circuit_instructions()
    target.add_instruction(MeasureReset(measure_reset_name), {(i,): None for i in qubits})
    return target


def two_qubit_circuit():
    """Return an empty circuit with two qubits and two single-clbit registers."""
    return QuantumCircuit(
        QuantumRegister(2, "q"), ClassicalRegister(1, "a"), ClassicalRegister(1, "b")
    )


def apply_x(circuit):
    """Apply an X gate to qubit 1."""
    circuit.x(1)


def apply_x_and_z(circuit):
    """Apply an X and a Z gate to qubit 1."""
    circuit.x(1)
    circuit.z(1)


def apply_x_on_both_qubits(circuit):
    """Apply an X gate to qubits 1 and 0."""
    circuit.x(1)
    circuit.x(0)


def measure_and_conditional_x(condition="clbit", before=None, body=apply_x, else_body=None):
    """Return a circuit measuring qubit 1 into clbit 0, followed by an ``if_else`` on clbit 0.

    Args:
        condition: ``"clbit"`` for ``(clbit, 1)``, ``"register"`` for ``(register, 1)`` on the
            single-clbit register of clbit 0, ``"expr"`` for ``expr.lift(clbit)``, ``"zero"`` for
            ``(clbit, 0)``, ``"register_zero"`` for ``(register, 0)``, or ``"other_clbit"`` for
            ``(other_clbit, 1)``.
        before: Function applied to the circuit between the measurement and the ``if_else``.
        body: Function applied to the circuit inside the ``if`` branch.
        else_body: Function applied to the circuit inside an ``else`` branch, if given.
    """
    circuit = two_qubit_circuit()
    circuit.measure(1, 0)
    if before is not None:
        before(circuit)
    clbit = circuit.clbits[0]
    condition = {
        "clbit": (clbit, 1),
        "register": (circuit.cregs[0], 1),
        "expr": expr.lift(clbit),
        "zero": (clbit, 0),
        "register_zero": (circuit.cregs[0], 0),
        "other_clbit": (circuit.clbits[1], 1),
    }[condition]
    with circuit.if_test(condition) as else_:
        body(circuit)
    if else_body is not None:
        with else_:
            else_body(circuit)
    return circuit


def measure_reset_circuit(name="measure_reset"):
    """Return the expected result of converting ``measure_and_conditional_x``."""
    circuit = two_qubit_circuit()
    circuit.append(MeasureReset(name), [1], [0])
    return circuit


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


@ddt
class TestConvertToMeasureReset(IBMTestCase):
    """Tests the conversion to MeasureReset in ConvertToMidCircuitResetAndMeasure."""

    def setUp(self):
        """Create a pass converting to MeasureReset on every qubit."""
        super().setUp()
        self.measure_reset_pass = ConvertToMidCircuitResetAndMeasure(
            target_with_measure_reset(), mcmr_name="measure_reset"
        )

    @data(
        {"condition": "clbit"},
        {"condition": "register"},
        {"condition": "expr"},
        {"body": lambda circuit: circuit.append(XGate(label="flip"), [1])},
    )
    def test_convert(self, circuit_kwargs):
        """Test that a measurement followed by a conditional X is replaced by MeasureReset."""
        circuit = measure_and_conditional_x(**circuit_kwargs)

        transpiled = PassManager([self.measure_reset_pass]).run(circuit)

        self.assertEqual(transpiled, measure_reset_circuit())

    def test_convert_custom_name(self):
        """Test the conversion to a MeasureReset instruction with a non-default name."""
        custom_pass = ConvertToMidCircuitResetAndMeasure(
            target_with_measure_reset("measure_reset_2"), mcmr_name="measure_reset_2"
        )
        transpiled = PassManager([custom_pass]).run(measure_and_conditional_x())

        self.assertEqual(transpiled, measure_reset_circuit("measure_reset_2"))

    def test_convert_reset_after_measure_simplification(self):
        """Test the conversion of the output of Qiskit's ResetAfterMeasureSimplification."""
        circuit = two_qubit_circuit()
        circuit.measure(1, 0)
        circuit.reset(1)
        simplified = PassManager([ResetAfterMeasureSimplification()]).run(circuit)

        transpiled = PassManager([self.measure_reset_pass]).run(simplified)

        self.assertEqual(transpiled, measure_reset_circuit())

    def test_convert_consecutive_patterns(self):
        """Test that consecutive patterns on the same qubit are all replaced."""
        circuit = measure_and_conditional_x()
        circuit.compose(measure_and_conditional_x(), inplace=True)

        transpiled = PassManager([self.measure_reset_pass]).run(circuit)

        self.assertEqual(transpiled.count_ops(), {"measure_reset": 2})

    @data(
        {"condition": "zero"},
        {"condition": "register_zero"},
        {"condition": "other_clbit"},
        {"before": lambda circuit: circuit.z(1)},
        {"before": lambda circuit: circuit.measure(0, 0)},
        {"body": lambda circuit: circuit.z(1)},
        {"body": apply_x_and_z},
        {"body": lambda circuit: circuit.x(0)},
        {"body": apply_x_on_both_qubits},
        {"else_body": lambda circuit: circuit.z(1)},
    )
    def test_not_converted(self, circuit_kwargs):
        """Test that variations of the pattern are not replaced by MeasureReset."""
        circuit = measure_and_conditional_x(**circuit_kwargs)

        transpiled = PassManager([self.measure_reset_pass]).run(circuit)

        self.assertNotIn("measure_reset", transpiled.count_ops())
        self.assertIn("if_else", transpiled.count_ops())

    def test_not_converted_if_else_on_two_qubits(self):
        """Test that the pattern is not replaced if the ``if_else`` acts on another qubit."""
        circuit = two_qubit_circuit()
        circuit.measure(1, 0)
        body = QuantumCircuit(2, 1)
        body.x(0)
        circuit.append(IfElseOp((circuit.clbits[0], 1), body), [1, 0], [0])

        transpiled = PassManager([self.measure_reset_pass]).run(circuit)

        self.assertNotIn("measure_reset", transpiled.count_ops())
        self.assertIn("if_else", transpiled.count_ops())

    @data(
        lambda circuit: (circuit.clbits[1], 1),
        lambda circuit: expr.lift(circuit.clbits[1]),
    )
    def test_not_converted_condition_on_other_clbit(self, condition):
        """Test that the pattern is not replaced if the condition is on another clbit.

        The ``if_else`` still depends on the measured clbit, as it is one of its ``cargs``.
        """
        circuit = two_qubit_circuit()
        circuit.measure(1, 0)
        body = QuantumCircuit(1, 1)
        body.x(0)
        circuit.append(IfElseOp(condition(circuit), body), [1], [0])

        transpiled = PassManager([self.measure_reset_pass]).run(circuit)

        self.assertNotIn("measure_reset", transpiled.count_ops())
        self.assertIn("if_else", transpiled.count_ops())

    def test_not_converted_multi_clbit_register(self):
        """Test that the pattern is not replaced if the condition is on a larger register."""
        register = ClassicalRegister(2, "c")
        circuit = QuantumCircuit(QuantumRegister(2, "q"), register)
        circuit.measure(1, 0)
        with circuit.if_test((register, 1)):
            circuit.x(1)

        transpiled = PassManager([self.measure_reset_pass]).run(circuit)

        self.assertNotIn("measure_reset", transpiled.count_ops())
        self.assertIn("if_else", transpiled.count_ops())

    def test_not_converted_inside_control_flow(self):
        """Test that the pattern is not replaced inside a control-flow block."""
        circuit = two_qubit_circuit()
        with circuit.if_test((circuit.clbits[1], 1)):
            circuit.measure(1, 0)
            with circuit.if_test((circuit.clbits[0], 1)):
                circuit.x(1)

        transpiled = PassManager([self.measure_reset_pass]).run(circuit)

        self.assertEqual(transpiled, circuit)

    def test_disabled_by_default(self):
        """Test that the pattern is not replaced if ``mcmr_name`` is not given."""
        custom_pass = ConvertToMidCircuitResetAndMeasure(target_with_measure_reset())
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            transpiled = PassManager([custom_pass]).run(measure_and_conditional_x())

        self.assertEqual(transpiled.count_ops(), {"measure_2": 1, "if_else": 1})

    def test_convert_with_mid_circuit_measure_and_reset(self):
        """Test that MeasureReset replacements happen before the other conversions."""
        circuit = measure_and_conditional_x()
        circuit.measure(0, 1)
        circuit.reset(0)
        circuit.measure_all()

        transpiled = PassManager([self.measure_reset_pass]).run(circuit)

        expected = measure_reset_circuit()
        expected.append(MidCircuitMeasure(), [0], [1])
        expected.append(MidCircuitReset(), [0])
        expected.measure_all()
        self.assertEqual(transpiled, expected)

    @data(
        ("measure_2", "must start with `measure_reset`"),
        ("measure_reset_3", "measure_reset_3 is not supported by the given target"),
    )
    def test_convert_raises(self, name_and_message):
        """Test that an invalid or unsupported ``mcmr_name`` raises a ValueError."""
        mcmr_name, message = name_and_message
        with self.assertRaisesRegex(ValueError, message):
            ConvertToMidCircuitResetAndMeasure(target_with_measure_reset(), mcmr_name=mcmr_name)

    def test_unsupported_qubit(self):
        """Test that the pattern is not replaced on qubits without MeasureReset support."""
        custom_pass = ConvertToMidCircuitResetAndMeasure(
            target_with_measure_reset(qubits=[0]), mcmr_name="measure_reset"
        )
        with self.assertWarnsRegex(UserWarning, "'measure_reset' with qubits \\[1\\]"):
            transpiled = PassManager([custom_pass]).run(measure_and_conditional_x())

        self.assertEqual(transpiled.count_ops(), {"measure_2": 1, "if_else": 1})
