# This code is part of Qiskit.
#
# (C) Copyright IBM 2022.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Test the dynamic circuits scheduling analysis"""

from unittest.mock import patch

from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister, transpile
from qiskit.pulse import Schedule, Play, Constant, DriveChannel
from qiskit.transpiler.passes import ConvertConditionsToIfOps
from qiskit.transpiler.passmanager import PassManager
from qiskit.transpiler.exceptions import TranspilerError
from qiskit.converters import circuit_to_dag
from qiskit.circuit import Delay

from qiskit_ibm_runtime.fake_provider import FakeJakartaV2
from qiskit_ibm_runtime.transpiler.passes.scheduling.pad_delay import PadDelay
from qiskit_ibm_runtime.transpiler.passes.scheduling.scheduler import (
    ALAPScheduleAnalysis,
    ASAPScheduleAnalysis,
)
from qiskit_ibm_runtime.transpiler.passes.scheduling.utils import (
    DynamicCircuitInstructionDurations,
)

from .....ibm_test_case import IBMTestCase

# pylint: disable=invalid-name,not-context-manager


class TestASAPSchedulingAndPaddingPass(IBMTestCase):
    """Tests the ASAP Scheduling passes"""

    def test_if_test_gate_after_measure(self):
        """Test if schedules circuits with c_if after measure with a common clbit.
        See: https://github.com/Qiskit/qiskit-terra/issues/7654"""
        qc = QuantumCircuit(2, 1)
        qc.measure(0, 0)
        with qc.if_test((0, 0)) as else_:
            qc.x(1)
        with else_:
            qc.x(0)

        durations = DynamicCircuitInstructionDurations([("x", None, 200), ("measure", None, 840)])
        pm = PassManager(
            [
                ASAPScheduleAnalysis(durations),
                PadDelay(durations, schedule_idle_qubits=True),
            ]
        )
        scheduled = pm.run(qc)

        expected = QuantumCircuit(2, 1)
        expected.delay(1000, 1)
        expected.measure(0, 0)
        with expected.if_test((0, 0)) as else_:
            expected.delay(200, 0)
            expected.x(1)
        with else_:
            expected.x(0)
            expected.delay(200, 1)

        self.assertEqual(expected, scheduled)

    def test_c_if_raises(self):
        """Verify that old format c_if raises an error."""
        qc = QuantumCircuit(2, 1)
        qc.measure(0, 0)
        qc.x(1).c_if(0, True)

        durations = DynamicCircuitInstructionDurations([("x", None, 200), ("measure", None, 840)])
        pm = PassManager(
            [
                ASAPScheduleAnalysis(durations),
                PadDelay(durations, schedule_idle_qubits=True),
            ]
        )
        with self.assertRaises(TranspilerError):
            pm.run(qc)

    def test_c_if_conversion(self):
        """Verify that old format c_if may be converted and scheduled."""
        qc = QuantumCircuit(1, 1)
        qc.x(0).c_if(0, True)

        durations = DynamicCircuitInstructionDurations([("x", None, 200), ("measure", None, 840)])
        pm = PassManager(
            [
                ConvertConditionsToIfOps(),
                ASAPScheduleAnalysis(durations),
                PadDelay(durations, schedule_idle_qubits=True),
            ]
        )
        scheduled = pm.run(qc)

        expected = QuantumCircuit(1, 1)
        with expected.if_test((0, 1)):
            expected.x(0)

        self.assertEqual(expected, scheduled)

    def test_measure_after_measure(self):
        """Test if schedules circuits with measure after measure with a common clbit.

        Note: There is no delay to write into the same clbit with IBM backends."""
        qc = QuantumCircuit(2, 1)
        qc.x(0)
        qc.measure(0, 0)
        qc.measure(1, 0)

        durations = DynamicCircuitInstructionDurations([("x", None, 200), ("measure", None, 840)])
        pm = PassManager(
            [
                ASAPScheduleAnalysis(durations),
                PadDelay(durations, schedule_idle_qubits=True),
            ]
        )
        scheduled = pm.run(qc)

        expected = QuantumCircuit(2, 1)
        expected.x(0)
        expected.delay(200, 1)
        expected.measure(0, 0)
        expected.measure(1, 0)
        self.assertEqual(expected, scheduled)

    def test_measure_block_not_end(self):
        """Tests that measures trigger do not trigger the end of a scheduling block."""
        qc = QuantumCircuit(3, 1)
        qc.x(0)
        qc.measure(0, 0)
        qc.measure(1, 0)
        qc.x(2)
        qc.measure(1, 0)
        qc.measure(2, 0)

        durations = DynamicCircuitInstructionDurations([("x", None, 200), ("measure", None, 840)])
        pm = PassManager(
            [
                ASAPScheduleAnalysis(durations),
                PadDelay(durations, schedule_idle_qubits=True),
            ]
        )
        scheduled = pm.run(qc)

        expected = QuantumCircuit(3, 1)
        expected.x(0)
        expected.delay(200, 1)
        expected.x(2)
        expected.delay(1000, 2)
        expected.measure(0, 0)
        expected.measure(1, 0)
        expected.delay(1000, 0)
        expected.measure(1, 0)
        expected.measure(2, 0)

        self.assertEqual(expected, scheduled)

    def test_reset_block_end(self):
        """Tests that measures trigger do trigger the end of a scheduling block."""
        qc = QuantumCircuit(3, 1)
        qc.x(0)
        qc.reset(0)
        qc.measure(1, 0)
        qc.x(2)
        qc.measure(1, 0)
        qc.measure(2, 0)

        durations = DynamicCircuitInstructionDurations(
            [("x", None, 200), ("measure", None, 840), ("reset", None, 840)]
        )
        pm = PassManager(
            [
                ASAPScheduleAnalysis(durations),
                PadDelay(durations, schedule_idle_qubits=True),
            ]
        )
        scheduled = pm.run(qc)

        expected = QuantumCircuit(3, 1)
        expected.x(0)
        expected.delay(200, 1)
        expected.x(2)
        expected.delay(1000, 2)
        expected.reset(0)
        expected.measure(1, 0)
        expected.barrier()
        expected.delay(1000, 0)
        expected.measure(1, 0)
        expected.measure(2, 0)

        self.assertEqual(expected, scheduled)

    def test_c_if_on_different_qubits(self):
        """Test if schedules circuits with `c_if`s on different qubits."""
        qc = QuantumCircuit(3, 1)
        qc.measure(0, 0)
        with qc.if_test((0, 1)):
            qc.x(1)
            qc.x(2)

        durations = DynamicCircuitInstructionDurations([("x", None, 200), ("measure", None, 840)])
        pm = PassManager(
            [
                ASAPScheduleAnalysis(durations),
                PadDelay(durations, schedule_idle_qubits=True),
            ]
        )
        scheduled = pm.run(qc)

        expected = QuantumCircuit(3, 1)
        expected.delay(1000, 1)
        expected.delay(1000, 2)
        expected.measure(0, 0)
        expected.barrier()
        with expected.if_test((0, 1)):
            expected.delay(200, 0)
            expected.x(1)
            expected.x(2)

        self.assertEqual(expected, scheduled)

    def test_shorter_measure_after_measure(self):
        """Test if schedules circuits with shorter measure after measure
        with a common clbit.

        Note: For dynamic circuits support we currently group measurements
        to start at the same time which in turn trigger the end of a block."""
        qc = QuantumCircuit(3, 1)
        qc.measure(0, 0)
        qc.measure(1, 0)

        durations = DynamicCircuitInstructionDurations(
            [("measure", [0], 840), ("measure", [1], 540)]
        )
        pm = PassManager(
            [
                ASAPScheduleAnalysis(durations),
                PadDelay(durations, schedule_idle_qubits=True),
            ]
        )
        scheduled = pm.run(qc)

        expected = QuantumCircuit(3, 1)
        expected.measure(0, 0)
        expected.measure(1, 0)
        expected.delay(300, 1)
        expected.delay(1000, 2)

        self.assertEqual(expected, scheduled)

    def test_measure_after_c_if(self):
        """Test if schedules circuits with c_if after measure with a common clbit."""
        qc = QuantumCircuit(3, 1)
        qc.measure(0, 0)
        with qc.if_test((0, 1)):
            qc.x(1)
        qc.measure(2, 0)

        durations = DynamicCircuitInstructionDurations([("x", None, 200), ("measure", None, 840)])
        pm = PassManager(
            [
                ASAPScheduleAnalysis(durations),
                PadDelay(durations, schedule_idle_qubits=True),
            ]
        )
        scheduled = pm.run(qc)

        expected = QuantumCircuit(3, 1)
        expected.delay(1000, 1)
        expected.delay(1000, 2)
        expected.measure(0, 0)
        expected.barrier()
        with expected.if_test((0, 1)):
            expected.delay(200, 0)
            expected.x(1)
            expected.delay(200, 2)

        expected.barrier()
        expected.delay(1000, 0)
        expected.measure(2, 0)
        expected.delay(1000, 1)

        self.assertEqual(expected, scheduled)

    def test_parallel_gate_different_length(self):
        """Test circuit having two parallel instruction with different length."""
        qc = QuantumCircuit(2, 2)
        qc.x(0)
        qc.x(1)
        qc.measure(0, 0)
        qc.measure(1, 1)

        durations = DynamicCircuitInstructionDurations(
            [("x", [0], 200), ("x", [1], 400), ("measure", None, 840)]
        )

        pm = PassManager(
            [
                ASAPScheduleAnalysis(durations),
                PadDelay(durations, schedule_idle_qubits=True),
            ]
        )
        scheduled = pm.run(qc)

        expected = QuantumCircuit(2, 2)
        expected.x(0)
        expected.x(1)
        expected.delay(200, 0)
        expected.measure(0, 0)  # immediately start after X gate
        expected.measure(1, 1)

        self.assertEqual(scheduled, expected)

    def test_parallel_gate_different_length_with_barrier(self):
        """Test circuit having two parallel instruction with different length with barrier."""
        qc = QuantumCircuit(2, 2)
        qc.x(0)
        qc.x(1)
        qc.barrier()
        qc.measure(0, 0)
        qc.measure(1, 1)

        durations = DynamicCircuitInstructionDurations(
            [("x", [0], 200), ("x", [1], 400), ("measure", None, 840)]
        )

        pm = PassManager(
            [
                ASAPScheduleAnalysis(durations),
                PadDelay(durations, schedule_idle_qubits=True),
            ]
        )
        scheduled = pm.run(qc)

        expected = QuantumCircuit(2, 2)
        expected.x(0)
        expected.delay(200, 0)
        expected.x(1)
        expected.barrier()
        expected.measure(0, 0)
        expected.measure(1, 1)

        self.assertEqual(scheduled, expected)

    def test_active_reset_circuit(self):
        """Test practical example of reset circuit.

        Because of the stimulus pulse overlap with the previous XGate on the q register,
        measure instruction is always triggered after XGate regardless of write latency.
        Thus only conditional latency matters in the scheduling."""
        qc = QuantumCircuit(1, 1)
        qc.measure(0, 0)
        with qc.if_test((0, 1)):
            qc.x(0)
        qc.measure(0, 0)
        with qc.if_test((0, 1)):
            qc.x(0)
        qc.measure(0, 0)
        with qc.if_test((0, 1)):
            qc.x(0)

        durations = DynamicCircuitInstructionDurations([("x", None, 100), ("measure", None, 840)])

        scheduled = PassManager(
            [
                ASAPScheduleAnalysis(durations),
                PadDelay(durations, schedule_idle_qubits=True),
            ]
        ).run(qc)

        expected = QuantumCircuit(1, 1)
        expected.measure(0, 0)
        with expected.if_test((0, 1)):
            expected.x(0)
        expected.measure(0, 0)
        with expected.if_test((0, 1)):
            expected.x(0)
        expected.measure(0, 0)
        with expected.if_test((0, 1)):
            expected.x(0)
        expected.barrier()

        self.assertEqual(expected, scheduled)

    def test_dag_introduces_extra_dependency_between_conditionals(self):
        """Test dependency between conditional operations in the scheduling.

        In the below example circuit, the conditional x on q1 could start at time 0,
        however it must be scheduled after the conditional x on q0 in scheduling.
        That is because circuit model used in the transpiler passes (DAGCircuit)
        interprets instructions acting on common clbits must be run in the order
        given by the original circuit (QuantumCircuit)."""
        qc = QuantumCircuit(2, 1)
        qc.delay(100, 0)
        with qc.if_test((0, 1)):
            qc.x(0)
        with qc.if_test((0, 1)):
            qc.x(1)

        durations = DynamicCircuitInstructionDurations([("x", None, 160)])
        pm = PassManager(
            [
                ASAPScheduleAnalysis(durations),
                PadDelay(durations, schedule_idle_qubits=True),
            ]
        )
        scheduled = pm.run(qc)

        expected = QuantumCircuit(2, 1)
        expected.delay(100, 0)
        expected.delay(100, 1)
        expected.barrier()
        with expected.if_test((0, 1)):
            expected.x(0)
            expected.delay(160, 1)
        with expected.if_test((0, 1)):
            expected.delay(160, 0)
            expected.x(1)

        self.assertEqual(expected, scheduled)

    def test_scheduling_with_calibration(self):
        """Test if calibrated instruction can update node duration."""
        qc = QuantumCircuit(2)
        qc.x(0)
        qc.cx(0, 1)
        qc.x(1)
        qc.cx(0, 1)

        xsched = Schedule(Play(Constant(300, 0.1), DriveChannel(0)))
        qc.add_calibration("x", (0,), xsched)

        durations = DynamicCircuitInstructionDurations([("x", None, 160), ("cx", None, 600)])
        pm = PassManager(
            [
                ASAPScheduleAnalysis(durations),
                PadDelay(durations, schedule_idle_qubits=True),
            ]
        )
        scheduled = pm.run(qc)

        expected = QuantumCircuit(2)
        expected.x(0)
        expected.delay(300, 1)
        expected.cx(0, 1)
        expected.x(1)
        expected.delay(160, 0)
        expected.cx(0, 1)
        expected.add_calibration("x", (0,), xsched)

        self.assertEqual(expected, scheduled)

    def test_padding_not_working_without_scheduling(self):
        """Test padding fails when un-scheduled DAG is input."""
        qc = QuantumCircuit(1, 1)
        qc.delay(100, 0)
        qc.x(0)
        qc.measure(0, 0)
        durations = DynamicCircuitInstructionDurations()

        with self.assertRaises(TranspilerError):
            PassManager(PadDelay(durations)).run(qc)

    def test_no_pad_very_end_of_circuit(self):
        """Test padding option that inserts no delay at the very end of circuit.

        This circuit will be unchanged after scheduling/padding."""
        qc = QuantumCircuit(2, 1)
        qc.delay(100, 0)
        qc.x(1)
        qc.measure(0, 0)

        durations = DynamicCircuitInstructionDurations([("x", None, 160), ("measure", None, 840)])

        scheduled = PassManager(
            [
                ASAPScheduleAnalysis(durations),
                PadDelay(durations, fill_very_end=False, schedule_idle_qubits=True),
            ]
        ).run(qc)

        expected = qc.copy()

        self.assertEqual(expected, scheduled)

    def test_reset_terminates_block(self):
        """Test if reset operations terminate the block scheduled.

        Note: For dynamic circuits support we currently group resets
        to start at the same time which in turn trigger the end of a block."""
        qc = QuantumCircuit(3, 1)
        qc.x(0)
        qc.reset(0)
        qc.measure(1, 0)
        qc.x(0)

        durations = DynamicCircuitInstructionDurations(
            [
                ("x", None, 200),
                (
                    "reset",
                    [0],
                    840,
                ),  # ignored as only the duration of the measurement is used for scheduling
                (
                    "reset",
                    [1],
                    740,
                ),  # ignored as only the duration of the measurement is used for scheduling
                ("measure", [0], 440),
                ("measure", [1], 540),
            ]
        )
        pm = PassManager(
            [
                ASAPScheduleAnalysis(durations),
                PadDelay(durations, schedule_idle_qubits=True),
            ]
        )
        scheduled = pm.run(qc)

        expected = QuantumCircuit(3, 1)
        expected.x(0)
        expected.delay(200, 1)
        expected.delay(900, 2)
        expected.reset(0)
        expected.delay(100, 0)
        expected.measure(1, 0)
        expected.barrier()
        expected.x(0)
        expected.delay(200, 1)
        expected.delay(200, 2)

        self.assertEqual(expected, scheduled)

    def test_reset_merged_with_measure(self):
        """Test if reset operations terminate the block scheduled.

        Note: For dynamic circuits support we currently group resets to start
        at the same time which in turn trigger the end of a block."""
        qc = QuantumCircuit(3, 1)
        qc.x(0)
        qc.reset(0)
        qc.measure(1, 0)

        durations = DynamicCircuitInstructionDurations(
            [
                ("x", None, 200),
                (
                    "reset",
                    [0],
                    840,
                ),  # ignored as only the duration of the measurement is used for scheduling
                (
                    "reset",
                    [1],
                    740,
                ),  # ignored as only the duration of the measurement is used for scheduling
                ("measure", [0], 440),
                ("measure", [1], 540),
            ]
        )
        pm = PassManager(
            [
                ASAPScheduleAnalysis(durations),
                PadDelay(durations, schedule_idle_qubits=True),
            ]
        )
        scheduled = pm.run(qc)

        expected = QuantumCircuit(3, 1)
        expected.x(0)
        expected.delay(200, 1)
        expected.delay(900, 2)
        expected.reset(0)
        expected.measure(1, 0)
        expected.delay(100, 0)

        self.assertEqual(expected, scheduled)

    def test_scheduling_is_idempotent(self):
        """Test that padding can be applied back to back without changing the circuit."""
        qc = QuantumCircuit(3, 2)
        qc.x(2)
        qc.cx(0, 1)
        qc.barrier()
        qc.measure(0, 0)
        with qc.if_test((0, 1)):
            qc.x(0)
        qc.measure(0, 0)
        with qc.if_test((0, 1)):
            qc.x(0)
        qc.measure(0, 0)
        with qc.if_test((0, 1)):
            qc.x(0)

        durations = DynamicCircuitInstructionDurations(
            [("x", None, 100), ("measure", None, 840), ("cx", None, 500)]
        )

        scheduled0 = PassManager(
            [
                ASAPScheduleAnalysis(durations),
                PadDelay(durations, schedule_idle_qubits=True),
            ]
        ).run(qc)

        scheduled1 = PassManager(
            [
                ASAPScheduleAnalysis(durations),
                PadDelay(durations, schedule_idle_qubits=True),
            ]
        ).run(scheduled0)

        self.assertEqual(scheduled0, scheduled1)

    def test_gate_on_measured_qubit(self):
        """Test that a gate on a previously measured qubit triggers the end of the block"""
        qc = QuantumCircuit(2, 1)
        qc.measure(0, 0)
        qc.x(0)
        qc.x(1)

        durations = DynamicCircuitInstructionDurations([("x", None, 200), ("measure", None, 840)])
        pm = PassManager(
            [
                ASAPScheduleAnalysis(durations),
                PadDelay(durations, schedule_idle_qubits=True),
            ]
        )
        scheduled = pm.run(qc)

        expected = QuantumCircuit(2, 1)
        expected.x(1)
        expected.delay(1000, 1)
        expected.measure(0, 0)
        expected.x(0)

        self.assertEqual(expected, scheduled)

    def test_grouped_measurements_prior_control_flow(self):
        """Test that measurements are grouped prior to control-flow"""
        qc = QuantumCircuit(3, 3)
        qc.measure(0, 0)
        qc.measure(1, 1)
        with qc.if_test((0, 1)):
            qc.x(2)
        with qc.if_test((1, 1)):
            qc.x(2)
        qc.measure(2, 2)

        durations = DynamicCircuitInstructionDurations([("x", None, 200), ("measure", None, 840)])
        pm = PassManager(
            [
                ASAPScheduleAnalysis(durations),
                PadDelay(durations, schedule_idle_qubits=True),
            ]
        )
        scheduled = pm.run(qc)

        expected = QuantumCircuit(3, 3)
        expected.delay(1000, 2)
        expected.measure(0, 0)
        expected.measure(1, 1)
        expected.barrier()
        with expected.if_test((0, 1)):
            expected.delay(200, 0)
            expected.delay(200, 1)
            expected.x(2)
        with expected.if_test((1, 1)):
            expected.delay(200, 0)
            expected.delay(200, 1)
            expected.x(2)
        expected.barrier()
        expected.delay(1000, 0)
        expected.delay(1000, 1)
        expected.measure(2, 2)

        self.assertEqual(expected, scheduled)

    def test_back_to_back_c_if(self):
        """Test back to back c_if scheduling"""

        qc = QuantumCircuit(3, 1)
        qc.delay(800, 1)
        with qc.if_test((0, 1)):
            qc.x(1)
        with qc.if_test((0, 1)):
            qc.x(2)

        qc.delay(1000, 2)
        qc.x(1)

        durations = DynamicCircuitInstructionDurations([("x", None, 200), ("measure", None, 840)])
        pm = PassManager(
            [
                ASAPScheduleAnalysis(durations),
                PadDelay(durations, schedule_idle_qubits=True),
            ]
        )
        scheduled = pm.run(qc)

        expected = QuantumCircuit(3, 1)
        expected.delay(800, 0)
        expected.delay(800, 1)
        expected.delay(800, 2)
        expected.barrier()
        with expected.if_test((0, 1)):
            expected.delay(200, 0)
            expected.x(1)
            expected.delay(200, 2)
        with expected.if_test((0, 1)):
            expected.delay(200, 0)
            expected.delay(200, 1)
            expected.x(2)
        expected.barrier()
        expected.delay(1000, 0)
        expected.x(1)
        expected.delay(800, 1)
        expected.delay(1000, 2)

        self.assertEqual(expected, scheduled)

    def test_nested_control_scheduling(self):
        """Test scheduling of nested control-flow"""

        qc = QuantumCircuit(4, 3)
        qc.x(0)
        with qc.if_test((0, 1)):
            qc.x(1)
            qc.measure(0, 1)
            with qc.if_test((1, 0)):
                qc.x(0)
                qc.measure(2, 2)
        qc.x(3)

        durations = DynamicCircuitInstructionDurations([("x", None, 200), ("measure", None, 840)])
        pm = PassManager(
            [
                ASAPScheduleAnalysis(durations),
                PadDelay(durations, schedule_idle_qubits=True),
            ]
        )
        scheduled = pm.run(qc)

        expected = QuantumCircuit(4, 3)
        expected.x(0)
        expected.delay(200, 1)
        expected.delay(200, 2)
        expected.delay(200, 3)
        expected.barrier()
        with expected.if_test((0, 1)):
            expected.measure(0, 1)
            expected.delay(1000, 1)
            expected.delay(1000, 2)
            expected.delay(1000, 3)
            expected.barrier()
            with expected.if_test((1, 0)):
                expected.x(0)
                expected.delay(800, 0)
                expected.delay(1000, 1)
                expected.measure(2, 2)
                expected.delay(1000, 3)
            expected.barrier()
            expected.delay(200, 0)
            expected.x(1)
            expected.delay(200, 2)
            expected.delay(200, 3)
        expected.barrier()
        expected.delay(200, 0)
        expected.delay(200, 1)
        expected.delay(200, 2)
        expected.x(3)

        self.assertEqual(expected, scheduled)

    def test_while_loop(self):
        """Test scheduling while loop"""

        qc = QuantumCircuit(2, 1)
        qc.x(0)
        with qc.while_loop((0, 1)):
            qc.x(1)
            qc.measure(0, 0)
        qc.x(0)

        durations = DynamicCircuitInstructionDurations([("x", None, 200), ("measure", None, 840)])
        pm = PassManager(
            [
                ASAPScheduleAnalysis(durations),
                PadDelay(durations, schedule_idle_qubits=True),
            ]
        )
        scheduled = pm.run(qc)

        expected = QuantumCircuit(2, 1)
        expected.x(0)
        expected.delay(200, 1)
        with expected.while_loop((0, 1)):
            expected.x(1)
            expected.delay(800, 1)
            expected.measure(0, 0)
        expected.x(0)
        expected.delay(200, 1)

        self.assertEqual(expected, scheduled)

    def test_for_loop(self):
        """Test scheduling for loop"""

        qc = QuantumCircuit(2, 1)
        qc.x(0)
        with qc.for_loop(range(2)):
            qc.x(1)
            qc.measure(0, 0)
        qc.x(0)

        durations = DynamicCircuitInstructionDurations([("x", None, 200), ("measure", None, 840)])
        pm = PassManager(
            [
                ASAPScheduleAnalysis(durations),
                PadDelay(durations, schedule_idle_qubits=True),
            ]
        )
        scheduled = pm.run(qc)

        expected = QuantumCircuit(2, 1)
        expected.x(0)
        expected.delay(200, 1)
        with expected.for_loop(range(2)):
            expected.x(1)
            expected.delay(800, 1)
            expected.measure(0, 0)
        expected.x(0)
        expected.delay(200, 1)

        self.assertEqual(expected, scheduled)

    def test_registers(self):
        """Verify scheduling works with registers."""
        qr = QuantumRegister(1, name="q")
        cr = ClassicalRegister(1)
        qc = QuantumCircuit(qr, cr)
        with qc.if_test((cr[0], True)):
            qc.x(qr[0])

        durations = DynamicCircuitInstructionDurations([("x", None, 200), ("measure", None, 840)])
        pm = PassManager(
            [
                ConvertConditionsToIfOps(),
                ASAPScheduleAnalysis(durations),
                PadDelay(durations, schedule_idle_qubits=True),
            ]
        )
        scheduled = pm.run(qc)

        expected = QuantumCircuit(qr, cr)
        with expected.if_test((cr[0], True)):
            expected.x(qr[0])

        self.assertEqual(expected, scheduled)

    def test_c_if_plugin_conversion_with_transpile(self):
        """Verify that old format c_if may be converted and scheduled
        after transpilation with the plugin."""
        # Patch the test backend with the plugin
        with patch.object(
            FakeJakartaV2,
            "get_translation_stage_plugin",
            return_value="ibm_dynamic_circuits",
            create=True,
        ):
            backend = FakeJakartaV2()

            durations = DynamicCircuitInstructionDurations.from_backend(backend)
            pm = PassManager(
                [
                    ASAPScheduleAnalysis(durations),
                    PadDelay(durations, schedule_idle_qubits=True),
                ]
            )

            qr0 = QuantumRegister(1, name="q")
            cr = ClassicalRegister(1, name="c")
            qc = QuantumCircuit(qr0, cr)
            qc.x(qr0[0]).c_if(cr[0], True)

            qc_transpiled = transpile(qc, backend, initial_layout=[0])

        scheduled = pm.run(qc_transpiled)

        qr1 = QuantumRegister(7, name="q")
        cr = ClassicalRegister(1, name="c")
        expected = QuantumCircuit(qr1, cr)
        with expected.if_test((cr[0], True)):
            expected.x(qr1[0])
            expected.delay(160, qr1[1])
            expected.delay(160, qr1[2])
            expected.delay(160, qr1[3])
            expected.delay(160, qr1[4])
            expected.delay(160, qr1[5])
            expected.delay(160, qr1[6])

        self.assertEqual(expected, scheduled)


class TestALAPSchedulingAndPaddingPass(IBMTestCase):
    """Tests the ALAP Scheduling passes"""

    def get_delay_dict(self, circ):
        """Return a dictionary with a list of delays for each qubit"""
        dag = circuit_to_dag(circ)
        delays = dag.op_nodes(Delay)
        delay_dict = {q_ind: [] for q_ind in range(len(circ.qubits))}
        for delay in delays:
            delay_dict[dag.find_bit(delay.qargs[0]).index] += [delay.op.duration]
        return delay_dict

    def test_alap(self):
        """Test standard ALAP scheduling"""
        durations = DynamicCircuitInstructionDurations([("x", None, 200), ("measure", None, 840)])
        qc = QuantumCircuit(3, 1)
        qc.measure(0, 0)
        qc.x(1)

        pm = PassManager(
            [
                ALAPScheduleAnalysis(durations),
                PadDelay(durations, schedule_idle_qubits=True),
            ]
        )
        scheduled = pm.run(qc)

        expected = QuantumCircuit(3, 1)
        expected.measure(0, 0)
        expected.delay(800, 1)
        expected.x(1)
        expected.delay(1000, 2)

        self.assertEqual(expected, scheduled)

    def test_if_test_gate_after_measure(self):
        """Test if schedules circuits with c_if after measure with a common clbit.
        See: https://github.com/Qiskit/qiskit-terra/issues/7654"""
        qc = QuantumCircuit(2, 1)
        qc.measure(0, 0)
        with qc.if_test((0, 0)) as else_:
            qc.x(1)
        with else_:
            qc.x(0)

        durations = DynamicCircuitInstructionDurations([("x", None, 200), ("measure", None, 840)])
        pm = PassManager(
            [
                ALAPScheduleAnalysis(durations),
                PadDelay(durations, schedule_idle_qubits=True),
            ]
        )
        scheduled = pm.run(qc)

        expected = QuantumCircuit(2, 1)
        expected.delay(1000, 1)
        expected.measure(0, 0)
        with expected.if_test((0, 0)) as else_:
            expected.delay(200, 0)
            expected.x(1)
        with else_:
            expected.x(0)
            expected.delay(200, 1)

        self.assertEqual(expected, scheduled)

    def test_classically_controlled_gate_after_measure(self):
        """Test if schedules circuits with c_if after measure with a common clbit.
        See: https://github.com/Qiskit/qiskit-terra/issues/7654"""
        qc = QuantumCircuit(2, 1)
        qc.measure(0, 0)
        with qc.if_test((0, True)):
            qc.x(1)

        durations = DynamicCircuitInstructionDurations([("x", None, 200), ("measure", None, 840)])
        pm = PassManager(
            [
                ALAPScheduleAnalysis(durations),
                PadDelay(durations, schedule_idle_qubits=True),
            ]
        )
        scheduled = pm.run(qc)

        expected = QuantumCircuit(2, 1)
        expected.delay(1000, 1)
        expected.measure(0, 0)
        expected.barrier()
        with expected.if_test((0, True)):
            expected.delay(200, 0)
            expected.x(1)

        self.assertEqual(expected, scheduled)

    def test_measure_after_measure(self):
        """Test if schedules circuits with measure after measure with a common clbit.

        Note: There is no delay to write into the same clbit with IBM backends."""
        qc = QuantumCircuit(2, 1)
        qc.x(0)
        qc.measure(0, 0)
        qc.measure(1, 0)

        durations = DynamicCircuitInstructionDurations([("x", None, 200), ("measure", None, 840)])
        pm = PassManager(
            [
                ALAPScheduleAnalysis(durations),
                PadDelay(durations, schedule_idle_qubits=True),
            ]
        )
        scheduled = pm.run(qc)

        expected = QuantumCircuit(2, 1)
        expected.x(0)
        expected.delay(200, 1)
        expected.measure(0, 0)
        expected.measure(1, 0)

        self.assertEqual(expected, scheduled)

    def test_measure_block_not_end(self):
        """Tests that measures trigger do not trigger the end of a scheduling block."""
        qc = QuantumCircuit(3, 1)
        qc.x(0)
        qc.measure(0, 0)
        qc.measure(1, 0)
        qc.x(2)
        qc.measure(1, 0)
        qc.measure(2, 0)

        durations = DynamicCircuitInstructionDurations([("x", None, 200), ("measure", None, 840)])
        pm = PassManager(
            [
                ALAPScheduleAnalysis(durations),
                PadDelay(durations, schedule_idle_qubits=True),
            ]
        )
        scheduled = pm.run(qc)

        expected = QuantumCircuit(3, 1)
        expected.x(0)
        expected.delay(200, 1)
        expected.delay(1000, 2)
        expected.x(2)
        expected.measure(0, 0)
        expected.delay(1000, 0)
        expected.measure(1, 0)
        expected.measure(1, 0)
        expected.measure(2, 0)

        self.assertEqual(expected, scheduled)

    def test_reset_block_end(self):
        """Tests that measures trigger do trigger the end of a scheduling block."""
        qc = QuantumCircuit(3, 1)
        qc.x(0)
        qc.reset(0)
        qc.measure(1, 0)
        qc.x(2)
        qc.measure(1, 0)
        qc.measure(2, 0)
        qc.measure(0, 0)

        durations = DynamicCircuitInstructionDurations(
            [("x", None, 200), ("measure", None, 840), ("reset", None, 840)]
        )
        pm = PassManager(
            [
                ALAPScheduleAnalysis(durations),
                PadDelay(durations, schedule_idle_qubits=True),
            ]
        )
        scheduled = pm.run(qc)

        expected = QuantumCircuit(3, 1)
        expected.x(0)
        expected.reset(0)
        expected.delay(200, 1)
        expected.delay(1000, 2)
        expected.x(2)
        expected.measure(1, 0)
        expected.barrier()
        expected.measure(1, 0)
        expected.measure(2, 0)
        expected.measure(0, 0)

        self.assertEqual(expected, scheduled)

    def test_c_if_on_different_qubits(self):
        """Test if schedules circuits with `c_if`s on different qubits."""
        qc = QuantumCircuit(3, 1)
        qc.measure(0, 0)
        with qc.if_test((0, 1)):
            qc.x(1)
            qc.x(2)

        durations = DynamicCircuitInstructionDurations([("x", None, 200), ("measure", None, 840)])
        pm = PassManager(
            [
                ALAPScheduleAnalysis(durations),
                PadDelay(durations, schedule_idle_qubits=True),
            ]
        )
        scheduled = pm.run(qc)

        expected = QuantumCircuit(3, 1)
        expected.delay(1000, 1)
        expected.delay(1000, 2)
        expected.measure(0, 0)
        expected.barrier()
        with expected.if_test((0, 1)):
            expected.delay(200, 0)
            expected.x(1)
            expected.x(2)

        self.assertEqual(expected, scheduled)

    def test_shorter_measure_after_measure(self):
        """Test if schedules circuits with shorter measure after measure
        with a common clbit.

        Note: For dynamic circuits support we currently group measurements
        to start at the same time which in turn trigger the end of a block."""
        qc = QuantumCircuit(3, 1)
        qc.measure(0, 0)
        qc.measure(1, 0)

        durations = DynamicCircuitInstructionDurations(
            [("measure", [0], 840), ("measure", [1], 540)]
        )
        pm = PassManager(
            [
                ALAPScheduleAnalysis(durations),
                PadDelay(durations, schedule_idle_qubits=True),
            ]
        )
        scheduled = pm.run(qc)

        expected = QuantumCircuit(3, 1)
        expected.delay(1000, 2)
        expected.measure(0, 0)
        expected.measure(1, 0)
        expected.delay(300, 1)

        self.assertEqual(expected, scheduled)

    def test_measure_after_c_if(self):
        """Test if schedules circuits with c_if after measure with a common clbit."""
        qc = QuantumCircuit(3, 1)
        qc.measure(0, 0)
        with qc.if_test((0, 1)):
            qc.x(1)
        qc.measure(2, 0)

        durations = DynamicCircuitInstructionDurations([("x", None, 200), ("measure", None, 840)])
        pm = PassManager(
            [
                ALAPScheduleAnalysis(durations),
                PadDelay(durations, schedule_idle_qubits=True),
            ]
        )
        scheduled = pm.run(qc)

        expected = QuantumCircuit(3, 1)
        expected.delay(1000, 1)
        expected.delay(1000, 2)
        expected.measure(0, 0)
        expected.barrier()
        with expected.if_test((0, 1)):
            expected.delay(200, 0)
            expected.x(1)
            expected.delay(200, 2)
        expected.barrier()
        expected.delay(1000, 0)
        expected.measure(2, 0)
        expected.delay(1000, 1)

        self.assertEqual(expected, scheduled)

    def test_parallel_gate_different_length(self):
        """Test circuit having two parallel instruction with different length."""
        qc = QuantumCircuit(2, 2)
        qc.x(0)
        qc.x(1)
        qc.measure(0, 0)
        qc.measure(1, 1)

        durations = DynamicCircuitInstructionDurations(
            [("x", [0], 200), ("x", [1], 400), ("measure", None, 840)]
        )

        pm = PassManager(
            [
                ALAPScheduleAnalysis(durations),
                PadDelay(durations, schedule_idle_qubits=True),
            ]
        )
        scheduled = pm.run(qc)

        expected = QuantumCircuit(2, 2)
        expected.delay(200, 0)
        expected.x(0)
        expected.x(1)
        expected.measure(0, 0)  # immediately start after X gate
        expected.measure(1, 1)

        self.assertEqual(scheduled, expected)

    def test_parallel_gate_different_length_with_barrier(self):
        """Test circuit having two parallel instruction with different length with barrier."""
        qc = QuantumCircuit(2, 2)
        qc.x(0)
        qc.x(1)
        qc.barrier()
        qc.measure(0, 0)
        qc.measure(1, 1)

        durations = DynamicCircuitInstructionDurations(
            [("x", [0], 200), ("x", [1], 400), ("measure", None, 840)]
        )

        pm = PassManager(
            [
                ALAPScheduleAnalysis(durations),
                PadDelay(durations, schedule_idle_qubits=True),
            ]
        )
        scheduled = pm.run(qc)

        expected = QuantumCircuit(2, 2)
        expected.delay(200, 0)
        expected.x(0)
        expected.x(1)
        expected.barrier()
        expected.measure(0, 0)
        expected.measure(1, 1)

        self.assertEqual(scheduled, expected)

    def test_active_reset_circuit(self):
        """Test practical example of reset circuit.

        Because of the stimulus pulse overlap with the previous XGate on the q register,
        measure instruction is always triggered after XGate regardless of write latency.
        Thus only conditional latency matters in the scheduling."""
        qc = QuantumCircuit(1, 1)
        qc.measure(0, 0)
        with qc.if_test((0, 1)):
            qc.x(0)
        qc.measure(0, 0)
        with qc.if_test((0, 1)):
            qc.x(0)
        qc.measure(0, 0)
        with qc.if_test((0, 1)):
            qc.x(0)

        durations = DynamicCircuitInstructionDurations([("x", None, 100), ("measure", None, 840)])

        scheduled = PassManager(
            [
                ALAPScheduleAnalysis(durations),
                PadDelay(durations, schedule_idle_qubits=True),
            ]
        ).run(qc)

        expected = QuantumCircuit(1, 1)
        expected.measure(0, 0)
        with expected.if_test((0, 1)):
            expected.x(0)
        expected.measure(0, 0)
        with expected.if_test((0, 1)):
            expected.x(0)
        expected.measure(0, 0)
        with expected.if_test((0, 1)):
            expected.x(0)
        expected.barrier()

        self.assertEqual(expected, scheduled)

    def test_dag_introduces_extra_dependency_between_conditionals(self):
        """Test dependency between conditional operations in the scheduling.

        In the below example circuit, the conditional x on q1 could start at time 0,
        however it must be scheduled after the conditional x on q0 in scheduling.
        That is because circuit model used in the transpiler passes (DAGCircuit)
        interprets instructions acting on common clbits must be run in the order
        given by the original circuit (QuantumCircuit)."""
        qc = QuantumCircuit(2, 1)
        qc.delay(100, 0)
        with qc.if_test((0, 1)):
            qc.x(0)
        with qc.if_test((0, 1)):
            qc.x(1)

        durations = DynamicCircuitInstructionDurations([("x", None, 160)])
        pm = PassManager(
            [
                ALAPScheduleAnalysis(durations),
                PadDelay(durations, schedule_idle_qubits=True),
            ]
        )
        scheduled = pm.run(qc)

        expected = QuantumCircuit(2, 1)
        expected.delay(100, 0)
        expected.delay(100, 1)
        expected.barrier()
        with expected.if_test((0, 1)):
            expected.x(0)
            expected.delay(160, 1)
        with expected.if_test((0, 1)):
            expected.delay(160, 0)
            expected.x(1)

        self.assertEqual(expected, scheduled)

    def test_scheduling_with_calibration(self):
        """Test if calibrated instruction can update node duration."""
        qc = QuantumCircuit(2)
        qc.x(0)
        qc.cx(0, 1)
        qc.x(1)
        qc.cx(0, 1)

        xsched = Schedule(Play(Constant(300, 0.1), DriveChannel(0)))
        qc.add_calibration("x", (0,), xsched)

        durations = DynamicCircuitInstructionDurations([("x", None, 160), ("cx", None, 600)])
        pm = PassManager(
            [
                ALAPScheduleAnalysis(durations),
                PadDelay(durations, schedule_idle_qubits=True),
            ]
        )
        scheduled = pm.run(qc)

        expected = QuantumCircuit(2)
        expected.x(0)
        expected.delay(300, 1)
        expected.cx(0, 1)
        expected.x(1)
        expected.delay(160, 0)
        expected.cx(0, 1)
        expected.add_calibration("x", (0,), xsched)

        self.assertEqual(expected, scheduled)

    def test_padding_not_working_without_scheduling(self):
        """Test padding fails when un-scheduled DAG is input."""
        qc = QuantumCircuit(1, 1)
        qc.delay(100, 0)
        qc.x(0)
        qc.measure(0, 0)
        durations = DynamicCircuitInstructionDurations()

        with self.assertRaises(TranspilerError):
            PassManager(PadDelay(durations)).run(qc)

    def test_no_pad_very_end_of_circuit(self):
        """Test padding option that inserts no delay at the very end of circuit.

        This circuit will be unchanged after scheduling/padding."""
        qc = QuantumCircuit(2, 1)
        qc.delay(100, 0)
        qc.x(1)
        qc.measure(0, 0)

        durations = DynamicCircuitInstructionDurations([("x", None, 160), ("measure", None, 840)])

        scheduled = PassManager(
            [
                ALAPScheduleAnalysis(durations),
                PadDelay(durations, fill_very_end=False, schedule_idle_qubits=True),
            ]
        ).run(qc)

        expected = QuantumCircuit(2, 1)
        expected.delay(100, 0)
        expected.measure(0, 0)
        expected.delay(940, 1)
        expected.x(1)

        self.assertEqual(expected, scheduled)

    def test_reset_terminates_block(self):
        """Test if reset operations terminate the block scheduled.

        Note: For dynamic circuits support we currently group resets
        to start at the same time which in turn trigger the end of a block."""
        qc = QuantumCircuit(3, 1)
        qc.x(0)
        qc.reset(0)
        qc.measure(1, 0)
        qc.x(0)

        durations = DynamicCircuitInstructionDurations(
            [
                ("x", None, 200),
                (
                    "reset",
                    [0],
                    840,
                ),  # ignored as only the duration of the measurement is used for scheduling
                (
                    "reset",
                    [1],
                    740,
                ),  # ignored as only the duration of the measurement is used for scheduling
                ("measure", [0], 440),
                ("measure", [1], 540),
            ]
        )
        pm = PassManager(
            [
                ALAPScheduleAnalysis(durations),
                PadDelay(durations, schedule_idle_qubits=True),
            ]
        )
        scheduled = pm.run(qc)

        expected = QuantumCircuit(3, 1)
        expected.x(0)
        expected.delay(200, 1)
        expected.delay(900, 2)
        expected.reset(0)
        expected.delay(100, 0)
        expected.measure(1, 0)
        expected.barrier()
        expected.x(0)
        expected.delay(200, 1)
        expected.delay(200, 2)

        self.assertEqual(expected, scheduled)

    def test_reset_merged_with_measure(self):
        """Test if reset operations terminate the block scheduled.

        Note: For dynamic circuits support we currently group resets to start
        at the same time which in turn trigger the end of a block."""
        qc = QuantumCircuit(3, 1)
        qc.x(0)
        qc.reset(0)
        qc.measure(1, 0)

        durations = DynamicCircuitInstructionDurations(
            [
                ("x", None, 200),
                (
                    "reset",
                    [0],
                    840,
                ),  # ignored as only the duration of the measurement is used for scheduling
                (
                    "reset",
                    [1],
                    740,
                ),  # ignored as only the duration of the measurement is used for scheduling
                ("measure", [0], 440),
                ("measure", [1], 540),
            ]
        )
        pm = PassManager(
            [
                ALAPScheduleAnalysis(durations),
                PadDelay(durations, schedule_idle_qubits=True),
            ]
        )
        scheduled = pm.run(qc)

        expected = QuantumCircuit(3, 1)
        expected.x(0)
        expected.delay(200, 1)
        expected.delay(900, 2)
        expected.reset(0)
        expected.delay(100, 0)
        expected.measure(1, 0)

        self.assertEqual(expected, scheduled)

    def test_already_scheduled(self):
        """Test no changes to pre-scheduled"""
        qc = QuantumCircuit(3, 2)
        qc.cx(0, 1)
        qc.delay(400, 2)
        qc.x(2)
        qc.barrier()
        qc.measure(0, 0)
        qc.delay(1000, 1)
        qc.delay(1000, 2)
        qc.barrier()
        with qc.if_test((0, 1)):
            qc.x(0)
            qc.delay(100, 1)
            qc.delay(100, 2)
        qc.barrier()
        qc.measure(0, 0)
        qc.delay(1000, 1)
        qc.delay(1000, 2)
        qc.barrier()

        durations = DynamicCircuitInstructionDurations(
            [("x", None, 100), ("measure", None, 840), ("cx", None, 500)]
        )

        scheduled = PassManager(
            [
                ALAPScheduleAnalysis(durations),
                PadDelay(durations, schedule_idle_qubits=True),
            ]
        ).run(qc)

        self.assertEqual(qc, scheduled)

    def test_scheduling_is_idempotent(self):
        """Test that padding can be applied back to back without changing the circuit."""
        qc = QuantumCircuit(3, 2)
        qc.x(2)
        qc.cx(0, 1)
        qc.barrier()
        qc.measure(0, 0)
        with qc.if_test((0, 1)):
            qc.x(0)
        qc.measure(0, 0)

        durations = DynamicCircuitInstructionDurations(
            [("x", None, 100), ("measure", None, 840), ("cx", None, 500)]
        )

        scheduled0 = PassManager(
            [
                ALAPScheduleAnalysis(durations),
                PadDelay(durations, schedule_idle_qubits=True),
            ]
        ).run(qc)

        scheduled1 = PassManager(
            [
                ALAPScheduleAnalysis(durations),
                PadDelay(durations, schedule_idle_qubits=True),
            ]
        ).run(scheduled0)

        self.assertEqual(scheduled0, scheduled1)

    def test_gate_on_measured_qubit(self):
        """Test that a gate on a previously measured qubit triggers the end of the block"""
        qc = QuantumCircuit(2, 1)
        qc.measure(0, 0)
        qc.x(0)
        qc.x(1)

        durations = DynamicCircuitInstructionDurations([("x", None, 200), ("measure", None, 840)])
        pm = PassManager(
            [
                ALAPScheduleAnalysis(durations),
                PadDelay(durations, schedule_idle_qubits=True),
            ]
        )
        scheduled = pm.run(qc)

        expected = QuantumCircuit(2, 1)
        expected.delay(1000, 1)
        expected.x(1)
        expected.measure(0, 0)
        expected.x(0)

        self.assertEqual(expected, scheduled)

    def test_grouped_measurements_prior_control_flow(self):
        """Test that measurements are grouped prior to control-flow"""
        qc = QuantumCircuit(3, 3)
        qc.measure(0, 0)
        qc.measure(1, 1)
        with qc.if_test((0, 1)):
            qc.x(2)
        with qc.if_test((1, 1)):
            qc.x(2)
        qc.measure(2, 2)

        durations = DynamicCircuitInstructionDurations([("x", None, 200), ("measure", None, 840)])
        pm = PassManager(
            [
                ALAPScheduleAnalysis(durations),
                PadDelay(durations, schedule_idle_qubits=True),
            ]
        )
        scheduled = pm.run(qc)

        expected = QuantumCircuit(3, 3)
        expected.delay(1000, 2)
        expected.measure(0, 0)
        expected.measure(1, 1)
        expected.barrier()
        with expected.if_test((0, 1)):
            expected.delay(200, 0)
            expected.delay(200, 1)
            expected.x(2)
        with expected.if_test((1, 1)):
            expected.delay(200, 0)
            expected.delay(200, 1)
            expected.x(2)
        expected.barrier()
        expected.delay(1000, 0)
        expected.delay(1000, 1)
        expected.measure(2, 2)

        self.assertEqual(expected, scheduled)

    def test_fast_path_eligible_scheduling(self):
        """Test scheduling of the fast-path eligible blocks.
        Verify that no barrier is inserted between measurements and fast-path conditionals.
        """
        qc = QuantumCircuit(4, 3)
        qc.x(0)
        qc.delay(1500, 1)
        qc.delay(1500, 2)
        qc.x(3)
        qc.barrier(1, 2, 3)
        qc.measure(0, 0)
        qc.measure(1, 1)
        with qc.if_test((0, 1)):
            qc.x(0)
        with qc.if_test((1, 1)):
            qc.x(1)
        qc.x(0)
        qc.x(0)
        qc.x(1)
        qc.x(2)

        durations = DynamicCircuitInstructionDurations([("x", None, 200), ("measure", None, 840)])
        pm = PassManager(
            [
                ALAPScheduleAnalysis(durations),
                PadDelay(durations, schedule_idle_qubits=True),
            ]
        )
        scheduled = pm.run(qc)

        expected = QuantumCircuit(4, 3)
        expected.delay(1300, 0)
        expected.x(0)
        expected.delay(1500, 1)
        expected.delay(1500, 2)
        expected.delay(1300, 3)
        expected.x(3)
        expected.barrier(1, 2, 3)
        expected.measure(0, 0)
        expected.measure(1, 1)
        expected.delay(1000, 2)
        expected.delay(1000, 3)
        with expected.if_test((0, 1)):
            expected.x(0)
        with expected.if_test((1, 1)):
            expected.x(1)
        expected.barrier()
        expected.x(0)
        expected.x(0)
        expected.delay(200, 1)
        expected.x(1)
        expected.delay(200, 2)
        expected.x(2)
        expected.delay(400, 3)

        self.assertEqual(expected, scheduled)

    def test_back_to_back_c_if(self):
        """Test back to back c_if scheduling"""

        qc = QuantumCircuit(3, 1)
        qc.delay(800, 1)
        with qc.if_test((0, 1)):
            qc.x(1)
        with qc.if_test((0, 1)):
            qc.x(2)

        qc.delay(1000, 2)
        qc.x(1)

        durations = DynamicCircuitInstructionDurations([("x", None, 200), ("measure", None, 840)])
        pm = PassManager(
            [
                ALAPScheduleAnalysis(durations),
                PadDelay(durations, schedule_idle_qubits=True),
            ]
        )
        scheduled = pm.run(qc)

        expected = QuantumCircuit(3, 1)
        expected.delay(800, 0)
        expected.delay(800, 1)
        expected.delay(800, 2)
        expected.barrier()
        with expected.if_test((0, 1)):
            expected.delay(200, 0)
            expected.x(1)
            expected.delay(200, 2)
        with expected.if_test((0, 1)):
            expected.delay(200, 0)
            expected.delay(200, 1)
            expected.x(2)
        expected.barrier()
        expected.delay(1000, 0)
        expected.delay(800, 1)
        expected.x(1)
        expected.delay(1000, 2)
        self.assertEqual(expected, scheduled)

    def test_issue_458_extra_idle_bug_0(self):
        """Regression test for https://github.com/Qiskit/qiskit-ibm-provider/issues/458

        This demonstrates that delays on idle qubits are pushed to the last schedulable
        region. This may happen if Terra's default scheduler is used and then the
        dynamic circuit scheduler is applied.
        """

        qc = QuantumCircuit(4, 3)

        qc.cx(0, 1)
        qc.delay(700, 0)
        qc.delay(700, 2)
        qc.cx(1, 2)
        qc.delay(3560, 3)
        qc.barrier([0, 1, 2])

        qc.delay(1160, 0)
        qc.delay(1000, 2)
        qc.measure(1, 0)
        qc.delay(160, 1)
        with qc.if_test((0, 1)):
            qc.x(2)
        qc.barrier([0, 1, 2])
        qc.measure(0, 1)
        qc.delay(1000, 1)
        qc.measure(2, 2)

        durations = DynamicCircuitInstructionDurations(
            [("x", None, 160), ("cx", None, 700), ("measure", None, 840)]
        )

        pm = PassManager(
            [
                ALAPScheduleAnalysis(durations),
                PadDelay(durations, schedule_idle_qubits=True),
            ]
        )
        scheduled = pm.run(qc)

        expected = QuantumCircuit(4, 3)
        expected.cx(0, 1)
        expected.delay(700, 0)
        expected.delay(700, 2)
        expected.cx(1, 2)
        expected.barrier([0, 1, 2])
        expected.delay(2560, 3)

        expected.delay(1160, 0)
        expected.delay(1160, 2)
        expected.measure(1, 0)
        expected.delay(160, 1)
        expected.barrier()
        with expected.if_test((0, 1)):
            expected.delay(160, 0)
            expected.delay(160, 1)
            expected.x(2)
            expected.delay(160, 3)
        expected.barrier()
        expected.delay(2560, 0)
        expected.delay(2560, 1)
        expected.delay(2560, 2)
        expected.delay(3560, 3)
        expected.barrier([0, 1, 2])
        expected.delay(1000, 1)
        expected.measure(0, 1)
        expected.measure(2, 2)

        self.assertEqual(scheduled, expected)

    def test_issue_458_extra_idle_bug_1(self):
        """Regression test for https://github.com/Qiskit/qiskit-ibm-provider/issues/458

        This demonstrates that a bug with a double-delay insertion has been resolved.
        """

        qc = QuantumCircuit(3, 3)

        qc.rz(0, 2)
        qc.barrier()
        qc.measure(1, 0)

        durations = DynamicCircuitInstructionDurations(
            [("rz", None, 0), ("cx", None, 700), ("measure", None, 840)]
        )

        pm = PassManager(
            [
                ALAPScheduleAnalysis(durations),
                PadDelay(durations, schedule_idle_qubits=True),
            ]
        )
        scheduled = pm.run(qc)

        expected = QuantumCircuit(3, 3)

        expected.rz(0, 2)
        expected.barrier()
        expected.delay(1000, 0)
        expected.measure(1, 0)
        expected.delay(1000, 2)

        self.assertEqual(scheduled, expected)

    def test_nested_control_scheduling(self):
        """Test scheduling of nested control-flow"""

        qc = QuantumCircuit(4, 3)
        qc.x(0)
        with qc.if_test((0, 1)):
            qc.x(1)
            qc.measure(0, 1)
            with qc.if_test((1, 0)):
                qc.x(0)
                qc.measure(2, 2)
        qc.x(3)

        durations = DynamicCircuitInstructionDurations([("x", None, 200), ("measure", None, 840)])
        pm = PassManager(
            [
                ALAPScheduleAnalysis(durations),
                PadDelay(durations, schedule_idle_qubits=True),
            ]
        )
        scheduled = pm.run(qc)

        expected = QuantumCircuit(4, 3)
        expected.x(0)
        expected.delay(200, 1)
        expected.delay(200, 2)
        expected.delay(200, 3)
        expected.barrier()
        with expected.if_test((0, 1)):
            expected.measure(0, 1)
            expected.delay(1000, 1)
            expected.delay(1000, 2)
            expected.delay(1000, 3)
            expected.barrier()
            with expected.if_test((1, 0)):
                expected.delay(800, 0)
                expected.x(0)
                expected.delay(1000, 1)
                expected.measure(2, 2)
                expected.delay(1000, 3)
            expected.barrier()
            expected.delay(200, 0)
            expected.x(1)
            expected.delay(200, 2)
            expected.delay(200, 3)
        expected.barrier()
        expected.delay(200, 0)
        expected.delay(200, 1)
        expected.delay(200, 2)
        expected.x(3)

        self.assertEqual(expected, scheduled)

    def test_while_loop(self):
        """Test scheduling while loop"""

        qc = QuantumCircuit(2, 1)
        qc.x(0)
        with qc.while_loop((0, 1)):
            qc.x(1)
            qc.measure(0, 0)
        qc.x(0)

        durations = DynamicCircuitInstructionDurations([("x", None, 200), ("measure", None, 840)])
        pm = PassManager(
            [
                ALAPScheduleAnalysis(durations),
                PadDelay(durations, schedule_idle_qubits=True),
            ]
        )
        scheduled = pm.run(qc)

        expected = QuantumCircuit(2, 1)
        expected.x(0)
        expected.delay(200, 1)
        with expected.while_loop((0, 1)):
            expected.delay(800, 1)
            expected.x(1)
            expected.measure(0, 0)
        expected.x(0)
        expected.delay(200, 1)

        self.assertEqual(expected, scheduled)

    def test_for_loop(self):
        """Test scheduling for loop"""

        qc = QuantumCircuit(2, 1)
        qc.x(0)
        with qc.for_loop(range(2)):
            qc.x(1)
            qc.measure(0, 0)
        qc.x(0)

        durations = DynamicCircuitInstructionDurations([("x", None, 200), ("measure", None, 840)])
        pm = PassManager(
            [
                ALAPScheduleAnalysis(durations),
                PadDelay(durations, schedule_idle_qubits=True),
            ]
        )
        scheduled = pm.run(qc)

        expected = QuantumCircuit(2, 1)
        expected.x(0)
        expected.delay(200, 1)
        with expected.for_loop(range(2)):
            expected.delay(800, 1)
            expected.x(1)
            expected.measure(0, 0)
        expected.x(0)
        expected.delay(200, 1)

        self.assertEqual(expected, scheduled)

    def test_transpile_mock_backend(self):
        """Test scheduling works with transpilation."""
        backend = FakeJakartaV2()

        durations = DynamicCircuitInstructionDurations.from_backend(backend)
        pm = PassManager(
            [
                ALAPScheduleAnalysis(durations),
                PadDelay(durations, schedule_idle_qubits=True),
            ]
        )

        qr = QuantumRegister(3)
        cr = ClassicalRegister(2)

        qc = QuantumCircuit(qr, cr)
        with qc.for_loop((cr[0], 1)):
            qc.x(qr[2])
            with qc.if_test((cr[0], 1)):
                qc.x(qr[1])
            qc.x(qr[0])

        qc_transpiled = transpile(qc, backend, initial_layout=[0, 1, 2])

        scheduled = pm.run(qc_transpiled)

        qr = QuantumRegister(7, name="q")
        expected = QuantumCircuit(qr, cr)
        with expected.for_loop((cr[0], 1)):
            with expected.if_test((cr[0], 1)):
                expected.delay(160, qr[0])
                expected.x(qr[1])
                expected.delay(160, qr[2])
                expected.delay(160, qr[3])
                expected.delay(160, qr[4])
                expected.delay(160, qr[5])
                expected.delay(160, qr[6])
            expected.barrier()
            expected.x(qr[0])
            expected.x(qr[2])
            expected.delay(160, qr[1])
            expected.delay(160, qr[3])
            expected.delay(160, qr[4])
            expected.delay(160, qr[5])
            expected.delay(160, qr[6])

        self.assertEqual(expected, scheduled)

    def test_transpile_both_paths(self):
        """Test scheduling works with both fast- and standard path after transpiling."""
        backend = FakeJakartaV2()

        durations = DynamicCircuitInstructionDurations.from_backend(backend)
        pm = PassManager(
            [
                ALAPScheduleAnalysis(durations),
                PadDelay(durations, schedule_idle_qubits=True),
            ]
        )

        qr = QuantumRegister(3)
        cr = ClassicalRegister(2)

        qc = QuantumCircuit(qr, cr)
        qc.measure(qr[0], cr[0])
        with qc.if_test((cr[0], 1)):
            qc.x(qr[0])
        with qc.if_test((cr[0], 1)):
            qc.x(qr[1])

        qc_transpiled = transpile(qc, backend, initial_layout=[0, 1, 2])

        scheduled = pm.run(qc_transpiled)

        qr = QuantumRegister(7, name="q")
        expected = QuantumCircuit(qr, cr)
        for q_ind in range(1, 7):
            expected.delay(24992, qr[q_ind])
        expected.measure(qr[0], cr[0])
        with expected.if_test((cr[0], 1)):
            expected.x(qr[0])
        with expected.if_test((cr[0], 1)):
            expected.x(qr[1])
            for q_ind in range(7):
                if q_ind != 1:
                    expected.delay(160, qr[q_ind])
        self.assertEqual(expected, scheduled)

    def test_c_if_plugin_conversion_with_transpile(self):
        """Verify that old format c_if may be converted and scheduled after
        transpilation with the plugin."""
        # Patch the test backend with the plugin
        with patch.object(
            FakeJakartaV2,
            "get_translation_stage_plugin",
            return_value="ibm_dynamic_circuits",
            create=True,
        ):
            backend = FakeJakartaV2()

            durations = DynamicCircuitInstructionDurations.from_backend(backend)
            pm = PassManager(
                [
                    ALAPScheduleAnalysis(durations),
                    PadDelay(durations, schedule_idle_qubits=True),
                ]
            )

            qr0 = QuantumRegister(1, name="q")
            cr = ClassicalRegister(1, name="c")
            qc = QuantumCircuit(qr0, cr)
            qc.x(qr0[0]).c_if(cr[0], True)

            qc_transpiled = transpile(qc, backend, initial_layout=[0])

        scheduled = pm.run(qc_transpiled)

        qr1 = QuantumRegister(7, name="q")
        cr = ClassicalRegister(1, name="c")
        expected = QuantumCircuit(qr1, cr)
        with expected.if_test((cr[0], True)):
            expected.x(qr1[0])
            expected.delay(160, qr1[1])
            expected.delay(160, qr1[2])
            expected.delay(160, qr1[3])
            expected.delay(160, qr1[4])
            expected.delay(160, qr1[5])
            expected.delay(160, qr1[6])

        self.assertEqual(expected, scheduled)

    def test_no_unused_qubits(self):
        """Test DD with if_test circuit that unused qubits are untouched and not scheduled.

        This ensures that programs don't have unnecessary information for unused qubits.
        Which might hurt performance in later execution stages.
        """

        durations = DynamicCircuitInstructionDurations([("x", None, 200), ("measure", None, 840)])
        pm = PassManager([ALAPScheduleAnalysis(durations), PadDelay(durations)])

        qc = QuantumCircuit(3, 1)
        qc.measure(0, 0)
        qc.x(1)
        with qc.if_test((0, True)):
            qc.x(1)
        qc.measure(0, 0)
        with qc.if_test((0, True)):
            qc.x(0)
        qc.x(1)

        scheduled = pm.run(qc)

        dont_use = scheduled.qubits[-1]
        for op in scheduled.data:
            self.assertNotIn(dont_use, op.qubits)

    def test_scheduling_nonuniform_durations(self):
        """Test that scheduling withing control flow blocks uses the
        instruction durations on the correct qubit indices"""

        backend = FakeJakartaV2()

        durations = DynamicCircuitInstructionDurations(
            [("cx", (0, 1), 250), ("cx", (1, 3), 4000), ("measure", None, 2600)]
        )
        pm = PassManager([ALAPScheduleAnalysis(durations), PadDelay(durations)])

        qc = QuantumCircuit(4, 1)
        qc.barrier()
        qc.measure(0, 0)
        with qc.if_test((0, True)):
            qc.cx(0, 1)
        qc_transpiled = transpile(qc, backend, initial_layout=[1, 3, 0, 2])
        scheduled = pm.run(qc_transpiled)
        delay_dict = self.get_delay_dict(scheduled.data[-1].operation.params[0])
        self.assertEqual(delay_dict[0][0], 4000)

        # different layout
        qc_transpiled = transpile(qc, backend, initial_layout=[0, 1, 2, 3])
        scheduled = pm.run(qc_transpiled)
        delay_dict = self.get_delay_dict(scheduled.data[-1].operation.params[0])
        self.assertEqual(delay_dict[2][0], 250)
