# This code is part of Qiskit.
#
# (C) Copyright IBM 2021.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Test dynamical decoupling insertion pass."""

import numpy as np
from numpy import pi

from ddt import ddt, data
from qiskit import pulse
from qiskit.circuit import QuantumCircuit, Delay
from qiskit.circuit.library import XGate, YGate, RXGate, UGate
from qiskit.quantum_info import Operator
from qiskit.transpiler.passmanager import PassManager
from qiskit.transpiler.exceptions import TranspilerError
from qiskit.transpiler.coupling import CouplingMap
from qiskit.converters import circuit_to_dag

from qiskit_ibm_runtime.transpiler.passes.scheduling.dynamical_decoupling import (
    PadDynamicalDecoupling,
)
from qiskit_ibm_runtime.transpiler.passes.scheduling.scheduler import (
    ASAPScheduleAnalysis,
)
from qiskit_ibm_runtime.transpiler.passes.scheduling.utils import (
    DynamicCircuitInstructionDurations,
)

from .....ibm_test_case import IBMTestCase

# pylint: disable=invalid-name,not-context-manager


@ddt
class TestPadDynamicalDecoupling(IBMTestCase):
    """Tests PadDynamicalDecoupling pass."""

    def setUp(self):
        """Circuits to test dynamical decoupling on."""
        super().setUp()

        self.ghz4 = QuantumCircuit(4)
        self.ghz4.h(0)
        self.ghz4.cx(0, 1)
        self.ghz4.cx(1, 2)
        self.ghz4.cx(2, 3)

        self.midmeas = QuantumCircuit(3, 1)
        self.midmeas.cx(0, 1)
        self.midmeas.cx(1, 2)
        self.midmeas.u(pi, 0, pi, 0)
        self.midmeas.measure(2, 0)
        self.midmeas.cx(1, 2)
        self.midmeas.cx(0, 1)

        self.durations = DynamicCircuitInstructionDurations(
            [
                ("h", 0, 50),
                ("cx", [0, 1], 700),
                ("cx", [1, 2], 200),
                ("cx", [2, 3], 300),
                ("x", None, 50),
                ("y", None, 50),
                ("u", None, 100),
                ("rx", None, 100),
                ("measure", None, 840),
                ("reset", None, 1340),
            ]
        )

        self.coupling_map = CouplingMap([[0, 1], [1, 2], [2, 3]])

    def test_insert_dd_ghz(self):
        """Test DD gates are inserted in correct spots."""
        dd_sequence = [XGate(), XGate()]
        pm = PassManager(
            [
                ASAPScheduleAnalysis(self.durations),
                PadDynamicalDecoupling(
                    self.durations,
                    dd_sequence,
                    pulse_alignment=1,
                    sequence_min_length_ratios=[1.0],
                    schedule_idle_qubits=True,
                ),
            ]
        )

        ghz4_dd = pm.run(self.ghz4)

        expected = self.ghz4.copy()
        expected = expected.compose(Delay(50), [1], front=True)
        expected = expected.compose(Delay(750), [2], front=True)
        expected = expected.compose(Delay(950), [3], front=True)

        expected = expected.compose(Delay(100), [0])
        expected = expected.compose(XGate(), [0])
        expected = expected.compose(Delay(200), [0])
        expected = expected.compose(XGate(), [0])
        expected = expected.compose(Delay(100), [0])

        expected = expected.compose(Delay(50), [1])
        expected = expected.compose(XGate(), [1])
        expected = expected.compose(Delay(100), [1])
        expected = expected.compose(XGate(), [1])
        expected = expected.compose(Delay(50), [1])

        self.assertEqual(ghz4_dd, expected)

    @data(True, False)
    def test_insert_dd_ghz_one_qubit(self, use_topological_ordering):
        """Test DD gates are inserted on only one qubit."""
        dd_sequence = [XGate(), XGate()]

        if use_topological_ordering:

            def _top_ord(dag):
                return dag.topological_op_nodes()

            block_ordering_callable = _top_ord
        else:
            block_ordering_callable = None

        pm = PassManager(
            [
                ASAPScheduleAnalysis(
                    durations=self.durations,
                    block_ordering_callable=block_ordering_callable,
                ),
                PadDynamicalDecoupling(
                    self.durations,
                    dd_sequence,
                    qubits=[0],
                    pulse_alignment=1,
                    schedule_idle_qubits=True,
                    block_ordering_callable=block_ordering_callable,
                ),
            ]
        )

        ghz4_dd = pm.run(self.ghz4.measure_all(inplace=False))

        expected = self.ghz4.copy()
        expected = expected.compose(Delay(50), [1], front=True)
        expected = expected.compose(Delay(750), [2], front=True)
        expected = expected.compose(Delay(950), [3], front=True)

        expected = expected.compose(Delay(100), [0])
        expected = expected.compose(XGate(), [0])
        expected = expected.compose(Delay(200), [0])
        expected = expected.compose(XGate(), [0])
        expected = expected.compose(Delay(100), [0])

        expected = expected.compose(Delay(300), [1])

        expected.measure_all()

        self.assertEqual(ghz4_dd, expected)

    def test_insert_dd_ghz_everywhere(self):
        """Test DD gates even on initial idle spots."""
        dd_sequence = [YGate(), YGate()]
        pm = PassManager(
            [
                ASAPScheduleAnalysis(self.durations),
                PadDynamicalDecoupling(
                    self.durations,
                    dd_sequence,
                    skip_reset_qubits=False,
                    pulse_alignment=1,
                    sequence_min_length_ratios=[0.0],
                    schedule_idle_qubits=True,
                ),
            ]
        )

        ghz4_dd = pm.run(self.ghz4)

        expected = self.ghz4.copy()
        expected = expected.compose(Delay(50), [1], front=True)

        expected = expected.compose(Delay(100), [0])
        expected = expected.compose(YGate(), [0])
        expected = expected.compose(Delay(200), [0])
        expected = expected.compose(YGate(), [0])
        expected = expected.compose(Delay(100), [0])

        expected = expected.compose(Delay(50), [1])
        expected = expected.compose(YGate(), [1])
        expected = expected.compose(Delay(100), [1])
        expected = expected.compose(YGate(), [1])
        expected = expected.compose(Delay(50), [1])

        expected = expected.compose(Delay(162), [2], front=True)
        expected = expected.compose(YGate(), [2], front=True)
        expected = expected.compose(Delay(326), [2], front=True)
        expected = expected.compose(YGate(), [2], front=True)
        expected = expected.compose(Delay(162), [2], front=True)

        expected = expected.compose(Delay(212), [3], front=True)
        expected = expected.compose(YGate(), [3], front=True)
        expected = expected.compose(Delay(426), [3], front=True)
        expected = expected.compose(YGate(), [3], front=True)
        expected = expected.compose(Delay(212), [3], front=True)

        self.assertEqual(ghz4_dd, expected)

    def test_insert_dd_ghz_xy4(self):
        """Test XY4 sequence of DD gates."""
        dd_sequence = [XGate(), YGate(), XGate(), YGate()]
        pm = PassManager(
            [
                ASAPScheduleAnalysis(self.durations),
                PadDynamicalDecoupling(
                    self.durations,
                    dd_sequence,
                    pulse_alignment=1,
                    sequence_min_length_ratios=[1.0],
                    schedule_idle_qubits=True,
                ),
            ]
        )

        ghz4_dd = pm.run(self.ghz4)

        expected = self.ghz4.copy()
        expected = expected.compose(Delay(50), [1], front=True)
        expected = expected.compose(Delay(750), [2], front=True)
        expected = expected.compose(Delay(950), [3], front=True)

        expected = expected.compose(Delay(37), [0])
        expected = expected.compose(XGate(), [0])
        expected = expected.compose(Delay(75), [0])
        expected = expected.compose(YGate(), [0])
        expected = expected.compose(Delay(76), [0])
        expected = expected.compose(XGate(), [0])
        expected = expected.compose(Delay(75), [0])
        expected = expected.compose(YGate(), [0])
        expected = expected.compose(Delay(37), [0])

        expected = expected.compose(Delay(12), [1])
        expected = expected.compose(XGate(), [1])
        expected = expected.compose(Delay(25), [1])
        expected = expected.compose(YGate(), [1])
        expected = expected.compose(Delay(26), [1])
        expected = expected.compose(XGate(), [1])
        expected = expected.compose(Delay(25), [1])
        expected = expected.compose(YGate(), [1])
        expected = expected.compose(Delay(12), [1])

        self.assertEqual(ghz4_dd, expected)

    @data(True, False)
    def test_insert_midmeas_hahn(self, use_topological_ordering):
        """Test a single X gate as Hahn echo can absorb in the upstream circuit."""
        dd_sequence = [RXGate(pi / 4)]

        if use_topological_ordering:

            def _top_ord(dag):
                return dag.topological_op_nodes()

            block_ordering_callable = _top_ord
        else:
            block_ordering_callable = None

        pm = PassManager(
            [
                ASAPScheduleAnalysis(
                    durations=self.durations,
                    block_ordering_callable=block_ordering_callable,
                ),
                PadDynamicalDecoupling(
                    self.durations,
                    dd_sequence,
                    pulse_alignment=1,
                    schedule_idle_qubits=True,
                    block_ordering_callable=block_ordering_callable,
                ),
            ]
        )

        midmeas_dd = pm.run(self.midmeas)

        combined_u = UGate(3 * pi / 4, -pi / 2, pi / 2)

        expected = QuantumCircuit(3, 1)
        expected.cx(0, 1)
        expected.compose(combined_u, [0], inplace=True)
        expected.delay(600, 0)
        expected.rx(pi / 4, 0)
        expected.delay(600, 0)
        expected.delay(700, 2)
        expected.cx(1, 2)
        expected.delay(1000, 1)
        expected.measure(2, 0)
        expected.cx(1, 2)
        expected.cx(0, 1)
        expected.delay(700, 2)

        self.assertEqual(midmeas_dd, expected)
        # check the absorption into U was done correctly
        self.assertTrue(
            Operator(XGate()).equiv(
                Operator(UGate(3 * pi / 4, -pi / 2, pi / 2)) & Operator(RXGate(pi / 4))
            )
        )

    def test_insert_ghz_uhrig(self):
        """Test custom spacing (following Uhrig DD [1]).
        [1] Uhrig, G. "Keeping a quantum bit alive by optimized π-pulse sequences."
        Physical Review Letters 98.10 (2007): 100504."""
        n = 8
        dd_sequence = [XGate()] * n

        # uhrig specifies the location of the k'th pulse
        def uhrig(k):
            return np.sin(np.pi * (k + 1) / (2 * n + 2)) ** 2

        # convert that to spacing between pulses (whatever finite duration pulses have)
        spacing = []
        for k in range(n):
            spacing.append(uhrig(k) - sum(spacing))
        spacing.append(1 - sum(spacing))

        pm = PassManager(
            [
                ASAPScheduleAnalysis(self.durations),
                PadDynamicalDecoupling(
                    self.durations,
                    dd_sequence,
                    qubits=[0],
                    spacings=spacing,
                    sequence_min_length_ratios=[0.0],
                    pulse_alignment=1,
                    schedule_idle_qubits=True,
                ),
            ]
        )

        ghz4_dd = pm.run(self.ghz4)

        expected = self.ghz4.copy()
        expected = expected.compose(Delay(50), [1], front=True)
        expected = expected.compose(Delay(750), [2], front=True)
        expected = expected.compose(Delay(950), [3], front=True)

        expected = expected.compose(Delay(3), [0])
        expected = expected.compose(XGate(), [0])
        expected = expected.compose(Delay(8), [0])
        expected = expected.compose(XGate(), [0])
        expected = expected.compose(Delay(13), [0])
        expected = expected.compose(XGate(), [0])
        expected = expected.compose(Delay(16), [0])
        expected = expected.compose(XGate(), [0])
        expected = expected.compose(Delay(20), [0])
        expected = expected.compose(XGate(), [0])
        expected = expected.compose(Delay(16), [0])
        expected = expected.compose(XGate(), [0])
        expected = expected.compose(Delay(13), [0])
        expected = expected.compose(XGate(), [0])
        expected = expected.compose(Delay(8), [0])
        expected = expected.compose(XGate(), [0])
        expected = expected.compose(Delay(3), [0])

        expected = expected.compose(Delay(300), [1])

        self.assertEqual(ghz4_dd, expected)

    def test_asymmetric_xy4_in_t2(self):
        """Test insertion of XY4 sequence with unbalanced spacing."""
        dd_sequence = [XGate(), YGate()] * 2
        spacing = [0] + [1 / 4] * 4
        pm = PassManager(
            [
                ASAPScheduleAnalysis(self.durations),
                PadDynamicalDecoupling(
                    self.durations,
                    dd_sequence,
                    pulse_alignment=1,
                    spacings=spacing,
                    schedule_idle_qubits=True,
                ),
            ]
        )

        t2 = QuantumCircuit(1)
        t2.h(0)
        t2.delay(2000, 0)
        t2.h(0)

        expected = QuantumCircuit(1)
        expected.h(0)
        expected.x(0)
        expected.delay(450, 0)
        expected.y(0)
        expected.delay(450, 0)
        expected.x(0)
        expected.delay(450, 0)
        expected.y(0)
        expected.delay(450, 0)
        expected.h(0)
        expected.global_phase = pi

        t2_dd = pm.run(t2)

        self.assertEqual(t2_dd, expected)
        # check global phase is correct
        self.assertEqual(Operator(t2), Operator(expected))

    def test_dd_after_reset(self):
        """Test skip_reset_qubits option works."""
        dd_sequence = [XGate(), XGate()]
        spacing = [0.1, 0.9]
        pm = PassManager(
            [
                ASAPScheduleAnalysis(self.durations),
                PadDynamicalDecoupling(
                    self.durations,
                    dd_sequence,
                    spacings=spacing,
                    skip_reset_qubits=True,
                    pulse_alignment=1,
                    sequence_min_length_ratios=[0.0],
                    schedule_idle_qubits=True,
                ),
            ]
        )

        t2 = QuantumCircuit(1)
        t2.reset(0)
        t2.delay(1000)
        t2.h(0)
        t2.delay(2000, 0)
        t2.h(0)

        expected = QuantumCircuit(1)
        expected.reset(0)
        expected.barrier()
        expected.delay(90)
        expected.x(0)
        expected.delay(810)
        expected.x(0)
        expected.h(0)
        expected.delay(190, 0)
        expected.x(0)
        expected.delay(1710, 0)
        expected.x(0)
        expected.h(0)

        t2_dd = pm.run(t2)

        self.assertEqual(t2_dd, expected)

    def test_insert_dd_bad_sequence(self):
        """Test DD raises when non-identity sequence is inserted."""
        dd_sequence = [XGate(), YGate()]
        pm = PassManager(
            [
                ASAPScheduleAnalysis(self.durations),
                PadDynamicalDecoupling(self.durations, dd_sequence, schedule_idle_qubits=True),
            ]
        )

        with self.assertRaises(TranspilerError):
            pm.run(self.ghz4)

    @data(0.5, 1.5)
    def test_dd_with_calibrations_with_parameters(self, param_value):
        """Check that calibrations in a circuit with parameters work fine."""

        circ = QuantumCircuit(2)
        circ.x(0)
        circ.cx(0, 1)
        circ.rx(param_value, 1)

        rx_duration = int(param_value * 1000)

        with pulse.build() as rx:
            pulse.play(
                pulse.Gaussian(rx_duration, 0.1, rx_duration // 4),
                pulse.DriveChannel(1),
            )

        circ.add_calibration("rx", (1,), rx, params=[param_value])

        durations = DynamicCircuitInstructionDurations([("x", None, 100), ("cx", None, 300)])

        dd_sequence = [XGate(), XGate()]
        pm = PassManager(
            [
                ASAPScheduleAnalysis(durations),
                PadDynamicalDecoupling(durations, dd_sequence, schedule_idle_qubits=True),
            ]
        )
        dd_circuit = pm.run(circ)

        for instruction in dd_circuit.data:
            op = instruction.operation
            if isinstance(op, RXGate):
                self.assertEqual(op.duration, rx_duration)

    def test_insert_dd_ghz_xy4_with_alignment(self):
        """Test DD with pulse alignment constraints."""
        dd_sequence = [XGate(), YGate(), XGate(), YGate()]
        pm = PassManager(
            [
                ASAPScheduleAnalysis(self.durations),
                PadDynamicalDecoupling(
                    self.durations,
                    dd_sequence,
                    pulse_alignment=10,
                    extra_slack_distribution="edges",
                    sequence_min_length_ratios=[1.0],
                    schedule_idle_qubits=True,
                ),
            ]
        )

        ghz4_dd = pm.run(self.ghz4)

        expected = self.ghz4.copy()
        expected = expected.compose(Delay(50), [1], front=True)
        expected = expected.compose(Delay(750), [2], front=True)
        expected = expected.compose(Delay(950), [3], front=True)

        expected = expected.compose(Delay(40), [0])
        expected = expected.compose(XGate(), [0])
        expected = expected.compose(Delay(70), [0])
        expected = expected.compose(YGate(), [0])
        expected = expected.compose(Delay(70), [0])
        expected = expected.compose(XGate(), [0])
        expected = expected.compose(Delay(70), [0])
        expected = expected.compose(YGate(), [0])
        expected = expected.compose(Delay(50), [0])

        expected = expected.compose(Delay(20), [1])
        expected = expected.compose(XGate(), [1])
        expected = expected.compose(Delay(20), [1])
        expected = expected.compose(YGate(), [1])
        expected = expected.compose(Delay(20), [1])
        expected = expected.compose(XGate(), [1])
        expected = expected.compose(Delay(20), [1])
        expected = expected.compose(YGate(), [1])
        expected = expected.compose(Delay(20), [1])

        self.assertEqual(ghz4_dd, expected)

    def test_dd_can_sequentially_called(self):
        """Test if sequentially called DD pass can output the same circuit.
        This test verifies:
        - if global phase is properly propagated from the previous padding node.
        - if node_start_time property is properly updated for new dag circuit.
        """
        dd_sequence = [XGate(), YGate(), XGate(), YGate()]

        pm1 = PassManager(
            [
                ASAPScheduleAnalysis(self.durations),
                PadDynamicalDecoupling(
                    self.durations, dd_sequence, qubits=[0], schedule_idle_qubits=True
                ),
                PadDynamicalDecoupling(
                    self.durations, dd_sequence, qubits=[1], schedule_idle_qubits=True
                ),
            ]
        )
        circ1 = pm1.run(self.ghz4)

        pm2 = PassManager(
            [
                ASAPScheduleAnalysis(self.durations),
                PadDynamicalDecoupling(
                    self.durations,
                    dd_sequence,
                    qubits=[0, 1],
                    schedule_idle_qubits=True,
                ),
            ]
        )
        circ2 = pm2.run(self.ghz4)

        self.assertEqual(circ1, circ2)

    def test_back_to_back_if_test(self):
        """Test DD with if_test circuit back to back."""

        dd_sequence = [XGate(), XGate()]
        pm = PassManager(
            [
                ASAPScheduleAnalysis(self.durations),
                PadDynamicalDecoupling(
                    self.durations,
                    dd_sequence,
                    pulse_alignment=1,
                    sequence_min_length_ratios=[0.0],
                    schedule_idle_qubits=True,
                ),
            ]
        )

        qc = QuantumCircuit(3, 1)
        qc.delay(800, 1)
        with qc.if_test((0, True)):
            qc.x(1)
        with qc.if_test((0, True)):
            qc.x(2)
        qc.delay(1000, 2)
        qc.x(1)

        qc_dd = pm.run(qc)

        expected = QuantumCircuit(3, 1)
        expected.delay(800, 0)
        expected.delay(800, 1)
        expected.delay(800, 2)
        expected.barrier()
        with expected.if_test((0, True)):
            expected.delay(50, 0)
            expected.x(1)
            expected.delay(50, 2)
        with expected.if_test((0, True)):
            expected.delay(50, 0)
            expected.delay(50, 1)
            expected.x(2)
        expected.barrier()
        expected.delay(1000, 0)
        expected.x(1)
        expected.delay(212, 1)
        expected.x(1)
        expected.delay(426, 1)
        expected.x(1)
        expected.delay(212, 1)
        expected.delay(225, 2)
        expected.x(2)
        expected.delay(450, 2)
        expected.x(2)
        expected.delay(225, 2)

        self.assertEqual(expected, qc_dd)

    def test_dd_if_test(self):
        """Test DD with if_test circuit."""

        dd_sequence = [XGate(), XGate()]
        pm = PassManager(
            [
                ASAPScheduleAnalysis(self.durations),
                PadDynamicalDecoupling(
                    self.durations,
                    dd_sequence,
                    pulse_alignment=1,
                    sequence_min_length_ratios=[0.0],
                    schedule_idle_qubits=True,
                ),
            ]
        )

        qc = QuantumCircuit(3, 1)
        qc.measure(0, 0)
        qc.x(2)
        qc.delay(1000, 1)
        with qc.if_test((0, True)):
            qc.x(1)
        qc.delay(8000, 1)
        with qc.if_test((0, True)):
            qc.x(2)
        qc.delay(1000, 2)
        qc.x(0)
        qc.x(2)

        qc_dd = pm.run(qc)

        expected = QuantumCircuit(3, 1)
        expected.delay(1000, 1)
        expected.x(2)
        expected.measure(0, 0)
        expected.delay(212, 2)
        expected.x(2)
        expected.delay(426, 2)
        expected.x(2)
        expected.delay(212, 2)
        expected.barrier()
        with expected.if_test((0, True)):
            expected.delay(50, 0)
            expected.x(1)
            expected.delay(50, 2)
        with expected.if_test((0, True)):
            expected.delay(50, 0)
            expected.delay(50, 1)
            expected.x(2)
        expected.barrier()
        expected.x(0)
        expected.delay(1962, 0)
        expected.x(0)
        expected.delay(3926, 0)
        expected.x(0)
        expected.delay(1962, 0)
        expected.delay(1975, 1)
        expected.x(1)
        expected.delay(3950, 1)
        expected.x(1)
        expected.delay(1975, 1)
        expected.delay(225, 2)
        expected.x(2)
        expected.delay(450, 2)
        expected.x(2)
        expected.delay(225, 2)
        expected.x(2)
        expected.delay(1712, 2)
        expected.x(2)
        expected.delay(3426, 2)
        expected.x(2)
        expected.delay(1712, 2)

        self.assertEqual(expected, qc_dd)

    def test_reproducible(self):
        """Test DD calls are reproducible."""

        qc = QuantumCircuit(3, 1)
        qc.measure(0, 0)
        qc.x(2)
        qc.delay(1000, 1)
        with qc.if_test((0, True)):
            qc.x(1)
        qc.delay(800, 1)
        with qc.if_test((0, True)):
            qc.x(2)
        qc.delay(1000, 2)
        qc.x(0)
        qc.x(2)

        dd_sequence = [XGate(), XGate()]
        pm0 = PassManager(
            [
                ASAPScheduleAnalysis(self.durations),
                PadDynamicalDecoupling(self.durations, dd_sequence, schedule_idle_qubits=True),
            ]
        )

        pm1 = PassManager(
            [
                ASAPScheduleAnalysis(self.durations),
                PadDynamicalDecoupling(self.durations, dd_sequence, schedule_idle_qubits=True),
            ]
        )
        qc_dd0 = pm0.run(qc)
        qc_dd1 = pm1.run(qc)

        self.assertEqual(qc_dd0, qc_dd1)

    def test_nested_block_dd(self):
        """Test DD applied within a block."""

        dd_sequence = [XGate(), XGate()]
        pm = PassManager(
            [
                ASAPScheduleAnalysis(self.durations),
                PadDynamicalDecoupling(
                    self.durations,
                    dd_sequence,
                    pulse_alignment=1,
                    sequence_min_length_ratios=[0.0],
                    schedule_idle_qubits=True,
                ),
            ]
        )

        qc = QuantumCircuit(3, 1)
        qc.x(1)
        qc.x(2)
        qc.barrier()
        with qc.if_test((0, True)):
            qc.delay(1000, 1)

        qc_dd = pm.run(qc)

        expected = QuantumCircuit(3, 1)
        expected.delay(50, 0)
        expected.x(1)
        expected.x(2)
        expected.barrier()
        with expected.if_test((0, True)):
            expected.delay(225, 1)
            expected.x(1)
            expected.delay(450, 1)
            expected.x(1)
            expected.delay(225, 1)
            expected.delay(225, 2)
            expected.x(2)
            expected.delay(450, 2)
            expected.x(2)
            expected.delay(225, 2)
            expected.delay(1000, 0)

        self.assertEqual(expected, qc_dd)

    def test_multiple_dd_sequences(self):
        """Test multiple DD sequence can be submitted"""

        qc = QuantumCircuit(2, 0)
        qc.x(0)  # First delay so qubits are touched
        qc.x(1)
        qc.delay(500, 0)
        qc.barrier()
        qc.delay(2000, 1)

        dd_sequence = [
            [XGate(), XGate(), XGate(), XGate(), XGate(), XGate(), XGate(), XGate()],
            [XGate(), XGate()],
        ]

        pm = PassManager(
            [
                ASAPScheduleAnalysis(self.durations),
                PadDynamicalDecoupling(
                    self.durations,
                    dd_sequence,
                    pulse_alignment=1,
                    sequence_min_length_ratios=[1.5, 0.0],
                    schedule_idle_qubits=True,
                ),
            ]
        )

        qc_dd = pm.run(qc)

        expected = QuantumCircuit(2, 0)
        expected.x(0)
        expected.delay(100, 0)
        expected.x(0)
        expected.delay(200, 0)
        expected.x(0)
        expected.delay(100, 0)
        expected.x(1)
        expected.delay(100, 1)
        expected.x(1)
        expected.delay(200, 1)
        expected.x(1)
        expected.delay(100, 1)
        expected.barrier()
        expected.delay(100, 0)
        expected.x(0)
        expected.delay(200, 0)
        expected.x(0)
        expected.delay(200, 0)
        expected.x(0)
        expected.delay(200, 0)
        expected.x(0)
        expected.delay(200, 0)
        expected.x(0)
        expected.delay(200, 0)
        expected.x(0)
        expected.delay(200, 0)
        expected.x(0)
        expected.delay(200, 0)
        expected.x(0)
        expected.delay(100, 0)
        expected.delay(100, 1)
        expected.x(1)
        expected.delay(200, 1)
        expected.x(1)
        expected.delay(200, 1)
        expected.x(1)
        expected.delay(200, 1)
        expected.x(1)
        expected.delay(200, 1)
        expected.x(1)
        expected.delay(200, 1)
        expected.x(1)
        expected.delay(200, 1)
        expected.x(1)
        expected.delay(200, 1)
        expected.x(1)
        expected.delay(100, 1)

        self.assertEqual(qc_dd, expected)

    def test_multiple_dd_sequence_cycles(self):
        """Test a single DD sequence can be inserted for multiple cycles in a single delay."""

        qc = QuantumCircuit(1, 0)
        qc.x(0)  # First delay so qubit is touched
        qc.delay(2000, 0)

        dd_sequence = [
            [XGate(), XGate()],
        ]  # cycle has length of 100 cycles

        pm = PassManager(
            [
                ASAPScheduleAnalysis(self.durations),
                PadDynamicalDecoupling(
                    self.durations,
                    dd_sequence,
                    extra_slack_distribution="edges",
                    pulse_alignment=1,
                    sequence_min_length_ratios=[10.0],
                    insert_multiple_cycles=True,
                    schedule_idle_qubits=True,
                ),
            ]
        )

        qc_dd = pm.run(qc)

        expected = QuantumCircuit(1, 0)
        expected.x(0)
        expected.delay(225, 0)
        expected.x(0)
        expected.delay(450, 0)
        expected.x(0)
        expected.delay(225, 0)
        expected.delay(225, 0)
        expected.x(0)
        expected.delay(450, 0)
        expected.x(0)
        expected.delay(225, 0)
        self.assertEqual(qc_dd, expected)

    def test_staggered_dd(self):
        """Test that timing on DD can be staggered if coupled with each other"""
        dd_sequence = [XGate(), XGate()]
        pm = PassManager(
            [
                ASAPScheduleAnalysis(self.durations),
                PadDynamicalDecoupling(
                    self.durations,
                    dd_sequence,
                    coupling_map=self.coupling_map,
                    alt_spacings=[0.1, 0.8, 0.1],
                    schedule_idle_qubits=True,
                ),
            ]
        )

        qc_barriers = QuantumCircuit(4, 1)
        qc_barriers.x(0)
        qc_barriers.x(1)
        qc_barriers.x(2)
        qc_barriers.x(3)
        qc_barriers.barrier()
        qc_barriers.measure(0, 0)
        qc_barriers.delay(14, 0)
        qc_barriers.x(1)
        qc_barriers.x(2)
        qc_barriers.x(3)
        qc_barriers.barrier()

        qc_dd = pm.run(qc_barriers)

        expected = QuantumCircuit(4, 1)
        expected.x(0)
        expected.x(1)
        expected.x(2)
        expected.x(3)
        expected.barrier()
        expected.x(1)
        expected.delay(208, 1)
        expected.x(1)
        expected.delay(448, 1)
        expected.x(1)
        expected.delay(208, 1)
        expected.x(2)
        expected.delay(80, 2)  # q1-q2 are coupled, staggered delays
        expected.x(2)
        expected.delay(704, 2)
        expected.x(2)
        expected.delay(80, 2)  # q2-q3 are uncoupled, same delays
        expected.x(3)
        expected.delay(208, 3)
        expected.x(3)
        expected.delay(448, 3)
        expected.x(3)
        expected.delay(208, 3)
        expected.measure(0, 0)
        expected.delay(14, 0)
        expected.barrier()

        self.assertEqual(qc_dd, expected)

    def test_staggered_dd_multiple_cycles(self):
        """Test staggered DD with multiple cycles in a single delay"""
        dd_sequence = [XGate(), XGate()]
        pm = PassManager(
            [
                ASAPScheduleAnalysis(self.durations),
                PadDynamicalDecoupling(
                    self.durations,
                    dd_sequence,
                    coupling_map=self.coupling_map,
                    alt_spacings=[0.1, 0.8, 0.1],
                    sequence_min_length_ratios=[4.0],
                    insert_multiple_cycles=True,
                    schedule_idle_qubits=True,
                ),
            ]
        )

        qc_barriers = QuantumCircuit(3, 1)
        qc_barriers.x(0)
        qc_barriers.x(1)
        qc_barriers.x(2)
        qc_barriers.barrier()
        qc_barriers.measure(0, 0)
        qc_barriers.delay(14, 0)
        qc_barriers.x(1)
        qc_barriers.x(2)
        qc_barriers.barrier()

        qc_dd = pm.run(qc_barriers)

        expected = QuantumCircuit(3, 1)
        expected.x(0)
        expected.x(1)
        expected.x(2)
        expected.barrier()
        expected.x(1)
        expected.delay(80, 1)
        expected.x(1)
        expected.delay(176, 1)
        expected.x(1)
        expected.delay(160, 1)
        expected.delay(80, 1)
        expected.x(1)
        expected.delay(176, 1)
        expected.x(1)
        expected.delay(92, 1)
        expected.x(2)
        expected.delay(32, 2)
        expected.x(2)
        expected.delay(304, 2)
        expected.x(2)
        expected.delay(48, 2)
        expected.delay(32, 2)
        expected.x(2)
        expected.delay(304, 2)
        expected.x(2)
        expected.delay(44, 2)
        expected.measure(0, 0)
        expected.delay(14, 0)
        expected.barrier()
        self.assertEqual(qc_dd, expected)

    def test_insert_dd_bad_spacings(self):
        """Test DD raises when spacings don't add up to 1."""
        dd_sequence = [XGate(), XGate()]
        pm = PassManager(
            [
                ASAPScheduleAnalysis(self.durations),
                PadDynamicalDecoupling(
                    self.durations,
                    dd_sequence,
                    spacings=[0.1, 0.9, 0.1],
                    coupling_map=self.coupling_map,
                ),
            ]
        )

        with self.assertRaises(TranspilerError):
            pm.run(self.ghz4)

    def test_insert_dd_bad_alt_spacings(self):
        """Test DD raises when alt_spacings don't add up to 1."""
        dd_sequence = [XGate(), XGate()]
        pm = PassManager(
            [
                ASAPScheduleAnalysis(self.durations),
                PadDynamicalDecoupling(
                    self.durations,
                    dd_sequence,
                    alt_spacings=[0.1, 0.9, 0.1],
                    coupling_map=self.coupling_map,
                ),
            ]
        )

        with self.assertRaises(TranspilerError):
            pm.run(self.ghz4)

    def test_unsupported_coupling_map(self):
        """Test DD raises if coupling map is not supported."""
        dd_sequence = [XGate(), XGate()]
        pm = PassManager(
            [
                ASAPScheduleAnalysis(self.durations),
                PadDynamicalDecoupling(
                    self.durations,
                    dd_sequence,
                    coupling_map=CouplingMap([[0, 1], [0, 2], [1, 2], [2, 3]]),
                ),
            ]
        )

        with self.assertRaises(TranspilerError):
            pm.run(self.ghz4)

    def test_disjoint_coupling_map(self):
        """Test staggered DD with disjoint coupling map."""
        qc = QuantumCircuit(5)
        for q in range(5):
            qc.x(q)
        qc.barrier()
        for q in range(5):
            qc.delay(1600, q)
        qc.barrier()
        dd_sequence = [XGate(), XGate()]
        pm = PassManager(
            [
                ASAPScheduleAnalysis(self.durations),
                PadDynamicalDecoupling(
                    self.durations,
                    dd_sequence,
                    coupling_map=CouplingMap([[0, 1], [1, 2], [3, 4]]),
                    schedule_idle_qubits=True,
                ),
            ]
        )
        dd_qc = pm.run(qc)

        # ensure that delays for nearest neighbors are staggered
        dag = circuit_to_dag(dd_qc)
        delays = dag.op_nodes(Delay)
        delay_dict = {q_ind: [] for q_ind in range(5)}
        for delay in delays:
            delay_dict[dag.find_bit(delay.qargs[0]).index] += [delay.op.duration]
        self.assertNotEqual(delay_dict[0], delay_dict[1])
        self.assertNotEqual(delay_dict[1], delay_dict[2])
        self.assertNotEqual(delay_dict[3], delay_dict[4])
        self.assertEqual(delay_dict[0], delay_dict[2])

    def test_no_unused_qubits(self):
        """Test DD with if_test circuit that unused qubits are untouched and
        not scheduled. Unused qubits may also have missing durations when
        not operational.
        This ensures that programs don't have unnecessary information for
        unused qubits.
        Which might hurt performance in later execution stages.
        """

        # Here "x" on qubit 3 is not defined
        durations = DynamicCircuitInstructionDurations(
            [
                ("h", 0, 50),
                ("x", 0, 50),
                ("x", 1, 50),
                ("x", 2, 50),
                ("measure", 0, 840),
                ("reset", 0, 1340),
            ]
        )

        dd_sequence = [XGate(), XGate()]
        pm = PassManager(
            [
                ASAPScheduleAnalysis(self.durations),
                PadDynamicalDecoupling(
                    durations,
                    dd_sequence,
                    pulse_alignment=1,
                    sequence_min_length_ratios=[0.0],
                ),
            ]
        )

        qc = QuantumCircuit(4, 1)
        qc.measure(0, 0)
        qc.x(1)
        with qc.if_test((0, True)):
            qc.x(0)
        qc.x(1)
        qc_dd = pm.run(qc)
        dont_use = qc_dd.qubits[-2:]
        for op in qc_dd.data:
            self.assertNotIn(dont_use, op.qubits)

    def test_dd_named_barriers(self):
        """Test DD applied on delays ending on named barriers."""

        dd_sequence = [XGate(), XGate()]
        pm = PassManager(
            [
                ASAPScheduleAnalysis(self.durations),
                PadDynamicalDecoupling(
                    self.durations,
                    dd_sequence,
                    pulse_alignment=1,
                    dd_barrier="dd",
                ),
            ]
        )

        qc = QuantumCircuit(2, 2)
        qc.h(0)
        qc.delay(1200, 0)
        qc.barrier()
        qc.delay(1200, 0)
        qc.measure(1, 0)
        qc.barrier(label="dd_0")
        qc.delay(1200, 0)
        qc.barrier(label="delay_only")
        qc.delay(1200, 1)
        qc_dd = pm.run(qc)
        # only 2 X gates are applied in the single delay
        # defined by the 'dd_0' barrier
        self.assertEqual(len([inst for inst in qc_dd.data if isinstance(inst.operation, XGate)]), 2)
