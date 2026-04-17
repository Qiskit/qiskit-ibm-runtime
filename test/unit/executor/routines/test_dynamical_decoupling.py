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

"""Tests for dynamical decoupling utilities."""

import unittest
import numpy as np

from qiskit.circuit import Delay, Parameter, QuantumCircuit
from qiskit.circuit.library import Measure, RZGate, XGate
from qiskit.transpiler import PassManager
from qiskit.transpiler.passes import (
    ALAPScheduleAnalysis,
    ASAPScheduleAnalysis,
    PadDelay,
    PadDynamicalDecoupling,
    TimeUnitConversion,
)
from qiskit_ibm_runtime.fake_provider import FakeManilaV2

from qiskit_ibm_runtime.executor.routines.options.dynamical_decoupling_options import (
    DynamicalDecouplingOptions,
)
from qiskit_ibm_runtime.executor.routines.dynamical_decoupling import (
    make_dd_sequence,
    generate_dd_pass_manager,
)


class TestMakeDDSequence(unittest.TestCase):
    """Tests for make_dd_sequence function."""

    def test_xx_sequence(self):
        """Test XX sequence generation."""
        dd_sequence, spacing = make_dd_sequence("XX")

        # Check dd_sequence
        self.assertEqual(len(dd_sequence), 2)
        self.assertIsInstance(dd_sequence[0], XGate)
        self.assertIsInstance(dd_sequence[1], XGate)

        # Check spacing
        self.assertEqual(len(spacing), 3)  # len(dd_sequence) + 1
        self.assertAlmostEqual(sum(spacing), 1.0)
        self.assertAlmostEqual(spacing[0], 0.25)  # delay/2
        self.assertAlmostEqual(spacing[1], 0.5)  # delay
        self.assertAlmostEqual(spacing[2], 0.25)  # delay/2

    def test_xpxm_sequence(self):
        """Test XpXm sequence generation."""
        dd_sequence, spacing = make_dd_sequence("XpXm")

        # Check dd_sequence: [XGate(), RZGate(π), XGate(), RZGate(-π)]
        self.assertEqual(len(dd_sequence), 4)
        self.assertIsInstance(dd_sequence[0], XGate)
        self.assertIsInstance(dd_sequence[1], RZGate)
        self.assertIsInstance(dd_sequence[2], XGate)
        self.assertIsInstance(dd_sequence[3], RZGate)

        # Check RZ angles
        self.assertAlmostEqual(dd_sequence[1].params[0], np.pi)
        self.assertAlmostEqual(dd_sequence[3].params[0], -np.pi)

        # Check spacing: [0.25, 0.5, 0, 0, 0.25]
        # First sequence (_xp) gets 0.25, second sequence (_xm) gets 0.5 then 2 zeros for its
        # extra gates
        self.assertEqual(len(spacing), 5)  # 2 sequences + 1
        self.assertAlmostEqual(sum(spacing), 1.0)
        self.assertAlmostEqual(spacing[0], 0.25)  # delay/2 before first sequence
        self.assertAlmostEqual(spacing[1], 0.5)  # delay before second sequence
        self.assertAlmostEqual(spacing[2], 0)  # zero for multi-gate sequence (_xm)
        self.assertAlmostEqual(spacing[3], 0)  # zero for multi-gate sequence (_xm)
        self.assertAlmostEqual(spacing[4], 0.25)  # delay/2 after last sequence

    def test_xy4_sequence(self):
        """Test XY4 sequence generation."""
        dd_sequence, spacing = make_dd_sequence("XY4")

        # XY4 has 4 sequences: [_xp, _yp, _xm, _ym]
        # _xp has 1 gate, _yp has 3 gates, _xm has 3 gates, _ym has 3 gates
        # Total gates: 1 + 3 + 3 + 3 = 10
        self.assertEqual(len(dd_sequence), 10)

        # Check spacing: [0.125, 0.25, 0, 0, 0.25, 0, 0, 0.25, 0, 0, 0.125]
        # Spacing has: initial + (4 sequences with delays) + (0+2+2+2 zeros for multi-gate) + final
        self.assertEqual(len(spacing), 11)  # 1 + 4 + 6 + 1 - 1 = 11
        self.assertAlmostEqual(sum(spacing), 1.0)

        # Check spacing values for 4 sequences
        self.assertAlmostEqual(spacing[0], 0.125)  # delay/2 for 4 sequences
        self.assertAlmostEqual(spacing[1], 0.25)  # delay for sequence 2
        self.assertAlmostEqual(spacing[4], 0.25)  # delay for sequence 3
        self.assertAlmostEqual(spacing[7], 0.25)  # delay for sequence 4
        self.assertAlmostEqual(spacing[10], 0.125)  # delay/2 at end

    def test_invalid_sequence_type(self):
        """Test that invalid sequence type raises ValueError."""
        with self.assertRaises(ValueError) as context:
            make_dd_sequence("INVALID")

        self.assertIn("Unknown sequence", str(context.exception))


class TestGenerateDDPassManager(unittest.TestCase):
    """Tests for generate_dd_pass_manager function."""

    def setUp(self):
        """Set up test fixtures."""
        self.backend = FakeManilaV2()

    def test_returns_pass_manager(self):
        """Test that function returns a PassManager."""
        options = DynamicalDecouplingOptions(enable=True, sequence_type="XX")
        pm = generate_dd_pass_manager(backend=self.backend, options=options)
        self.assertIsInstance(pm, PassManager)

    def test_pass_manager_has_correct_number_of_passes(self):
        """Test that pass manager contains exactly 4 passes."""
        options = DynamicalDecouplingOptions(enable=True, sequence_type="XX")
        pm = generate_dd_pass_manager(backend=self.backend, options=options)

        flow_controller = pm.to_flow_controller()
        passes = flow_controller.passes

        # Should have: TimeUnitConversion, Scheduling, PadDynamicalDecoupling, PadDelay
        self.assertEqual(len(passes), 4)

    def test_alap_scheduling_pass_is_used(self):
        """Test that ALAP scheduling pass is used when specified."""
        options = DynamicalDecouplingOptions(
            enable=True, sequence_type="XX", scheduling_method="alap"
        )
        pm = generate_dd_pass_manager(backend=self.backend, options=options)

        flow_controller = pm.to_flow_controller()
        passes = flow_controller.passes

        # Second pass should be ALAPScheduleAnalysis
        self.assertIsInstance(passes[1], ALAPScheduleAnalysis)

    def test_asap_scheduling_pass_is_used(self):
        """Test that ASAP scheduling pass is used when specified."""
        options = DynamicalDecouplingOptions(
            enable=True, sequence_type="XX", scheduling_method="asap"
        )
        pm = generate_dd_pass_manager(backend=self.backend, options=options)

        flow_controller = pm.to_flow_controller()
        passes = flow_controller.passes

        # Second pass should be ASAPScheduleAnalysis
        self.assertIsInstance(passes[1], ASAPScheduleAnalysis)

    def test_time_unit_conversion_pass_is_first(self):
        """Test that TimeUnitConversion is the first pass."""
        options = DynamicalDecouplingOptions(enable=True, sequence_type="XX")
        pm = generate_dd_pass_manager(backend=self.backend, options=options)

        flow_controller = pm.to_flow_controller()
        passes = flow_controller.passes

        self.assertIsInstance(passes[0], TimeUnitConversion)

    def test_pad_dynamical_decoupling_pass_has_correct_target(self):
        """Test that PadDynamicalDecoupling pass has correct target."""
        options = DynamicalDecouplingOptions(enable=True, sequence_type="XX")
        pm = generate_dd_pass_manager(backend=self.backend, options=options)

        flow_controller = pm.to_flow_controller()
        passes = flow_controller.passes

        # Third pass should be PadDynamicalDecoupling
        dd_pass = passes[2]
        self.assertIsInstance(dd_pass, PadDynamicalDecoupling)
        self.assertEqual(dd_pass.target, self.backend.target)

    def test_pad_dynamical_decoupling_pass_has_xx_sequence(self):
        """Test that PadDynamicalDecoupling has correct XX sequence."""
        options = DynamicalDecouplingOptions(enable=True, sequence_type="XX")
        pm = generate_dd_pass_manager(backend=self.backend, options=options)

        flow_controller = pm.to_flow_controller()
        dd_pass = flow_controller.passes[2]

        # XX sequence should have 2 X gates
        self.assertEqual(len(dd_pass._dd_sequence), 2)
        self.assertIsInstance(dd_pass._dd_sequence[0], XGate)
        self.assertIsInstance(dd_pass._dd_sequence[1], XGate)

    def test_pad_dynamical_decoupling_pass_has_xpxm_sequence(self):
        """Test that PadDynamicalDecoupling has correct XpXm sequence."""
        options = DynamicalDecouplingOptions(enable=True, sequence_type="XpXm")
        pm = generate_dd_pass_manager(backend=self.backend, options=options)

        flow_controller = pm.to_flow_controller()
        dd_pass = flow_controller.passes[2]

        # XpXm sequence should have 4 gates: X, RZ(π), X, RZ(-π)
        self.assertEqual(len(dd_pass._dd_sequence), 4)
        self.assertIsInstance(dd_pass._dd_sequence[0], XGate)
        self.assertIsInstance(dd_pass._dd_sequence[1], RZGate)
        self.assertIsInstance(dd_pass._dd_sequence[2], XGate)
        self.assertIsInstance(dd_pass._dd_sequence[3], RZGate)

    def test_pad_dynamical_decoupling_pass_has_xy4_sequence(self):
        """Test that PadDynamicalDecoupling has correct XY4 sequence."""
        options = DynamicalDecouplingOptions(enable=True, sequence_type="XY4")
        pm = generate_dd_pass_manager(backend=self.backend, options=options)

        flow_controller = pm.to_flow_controller()
        dd_pass = flow_controller.passes[2]

        # XY4 sequence should have 10 gates total
        self.assertEqual(len(dd_pass._dd_sequence), 10)

    def test_pad_dynamical_decoupling_pass_extra_slack_distribution_is_propagated(self):
        """Test that extra_slack_distribution is propagated."""
        options = DynamicalDecouplingOptions(
            enable=True,
            sequence_type="XX",
            extra_slack_distribution="edges",
        )
        pm = generate_dd_pass_manager(backend=self.backend, options=options)

        flow_controller = pm.to_flow_controller()
        dd_pass = flow_controller.passes[2]

        self.assertEqual(dd_pass._extra_slack_distribution, "edges")

    def test_pad_dynamical_decoupling_pass_skip_reset_qubits_is_propagated(self):
        """Test that skip_reset_qubits is propagated."""
        options = DynamicalDecouplingOptions(
            enable=True, sequence_type="XX", skip_reset_qubits=False
        )
        pm = generate_dd_pass_manager(backend=self.backend, options=options)

        flow_controller = pm.to_flow_controller()
        dd_pass = flow_controller.passes[2]

        self.assertFalse(dd_pass._skip_reset_qubits)

    def test_pad_delay_pass_is_last(self):
        """Test that PadDelay is the last pass."""
        options = DynamicalDecouplingOptions(enable=True, sequence_type="XX")
        pm = generate_dd_pass_manager(backend=self.backend, options=options)

        flow_controller = pm.to_flow_controller()
        passes = flow_controller.passes

        # Last pass should be PadDelay
        self.assertIsInstance(passes[3], PadDelay)
        self.assertEqual(passes[3].target, self.backend.target)

    def test_backend_without_target_raises_error(self):
        """Test that backend without target raises ValueError."""

        # Create a mock backend without target
        class MockBackend:
            """Mock backend without target for testing."""

            target = None

        options = DynamicalDecouplingOptions(enable=True, sequence_type="XX")

        with self.assertRaises(ValueError) as context:
            generate_dd_pass_manager(backend=MockBackend(), options=options)  # type: ignore

        self.assertIn("must have a target", str(context.exception))

    def test_pass_manager_applies_xx_sequence_correctly(self):
        """Test that XX DD sequence is applied correctly to circuit."""
        backend = FakeManilaV2()
        options = DynamicalDecouplingOptions(enable=True, sequence_type="XX")
        pm = generate_dd_pass_manager(backend=backend, options=options)

        # Create test circuit with idle time on qubit 2
        circuit = QuantumCircuit(3)
        circuit.cx(0, 1)
        circuit.rz(Parameter("a"), 2)
        circuit.measure_all()

        # Run pass manager
        result_circuit = pm.run(circuit)

        cx_duration_seconds = backend.target["cx"][(0, 1)].duration
        x_duration_seconds = backend.target["x"][(2,)].duration
        dt = backend.target.dt
        granualrity = backend.target.granularity
        cx_duration_dt = int(cx_duration_seconds / dt)
        x_duration_dt = int(x_duration_seconds / dt)

        # Verify DD sequence on qubit 2
        expected_stream = [Delay, XGate, Delay, XGate, Delay, RZGate, Measure]
        expected_iter = iter(expected_stream)

        # Collect delays on qubit 2
        delays_q2 = []

        for instruction in result_circuit:
            if instruction.qubits == (circuit.qubits[2],):
                self.assertIsInstance(instruction.operation, next(expected_iter))
                if isinstance(instruction.operation, Delay):
                    delays_q2.append(instruction.operation.duration)

        self.assertEqual(len(delays_q2), 3)

        # Verify the duration of the 3 delays + 2 x gates sum to CX duration (idle time on qubit 2)
        total_delay = sum(delays_q2)
        total_dd_duration = total_delay + 2 * x_duration_dt
        self.assertEqual(total_dd_duration, cx_duration_dt)

        # For XX sequence, spacing is [0.25, 0.5, 0.25] of total delay time, but granularity is
        # enforced.
        self.assertAlmostEqual(
            delays_q2[0], np.floor(total_delay * 0.25 / granualrity) * granualrity
        )
        self.assertAlmostEqual(
            delays_q2[2], np.floor(total_delay * 0.25 / granualrity) * granualrity
        )
