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

"""Unit tests for the circuit schedule class."""

import ddt
import numpy as np
from qiskit_ibm_runtime.visualization.utils import plotly_module
from qiskit_ibm_runtime.utils.circuit_schedule import CircuitSchedule
from ..ibm_test_case import IBMTestCase
from .mock.fake_circuit_schedule_timing import FakeCircuitScheduleInputData


@ddt.ddt
class TestCircuitSchedule(IBMTestCase):
    """Tests for CircuitSchedule class."""

    def setUp(self) -> None:
        """Set up."""
        fake_sampler_pub_result_large = FakeCircuitScheduleInputData.sampler_pub_result_large
        fake_sampler_pub_result_small = FakeCircuitScheduleInputData.sampler_pub_result_small
        self.circuit_schedule_large_data = fake_sampler_pub_result_large.metadata["compilation"][
            "scheduler_timing"
        ]["timing"]
        self.circuit_schedule_small_data = fake_sampler_pub_result_small.metadata["compilation"][
            "scheduler_timing"
        ]["timing"]

    def get_large_mock_data(self):
        """Return the whole data object"""
        return self.circuit_schedule_large_data

    def get_small_mock_data(self):
        """Return small constant portion of data object"""
        return self.circuit_schedule_small_data

    def test__load(self):
        """Test data loading"""
        data = self.get_small_mock_data()
        loaded_data = CircuitSchedule._load(data)
        expected_loaded_data = self.get_small_mock_data().split("\n")
        self.assertEqual(loaded_data, expected_loaded_data)

    def test__parse(self):
        """Test circuit schedule data parsing"""
        data = self.get_small_mock_data()
        circuit_schedule = CircuitSchedule(data)
        self.assertIsNotNone(circuit_schedule.circuit_scheduling)

        expected_circuit_scheduling = [
            ["main", "barrier", "Qubit 0", "7", "7", "barrier", "barrier"],
            ["main", "barrier", "Qubit 1", "7", "7", "barrier", "barrier"],
            ["main", "barrier", "Qubit 2", "7", "7", "barrier", "barrier"],
            ["main", "barrier", "Qubit 3", "7", "7", "barrier", "barrier"],
            ["main", "barrier", "Qubit 4", "7", "7", "barrier", "barrier"],
        ]
        self.assertTrue(np.all(circuit_schedule.circuit_scheduling == expected_circuit_scheduling))

        circuit_schedule = CircuitSchedule(data)
        self.assertIsNotNone(circuit_schedule.circuit_scheduling)
        self.assertTrue(np.all(circuit_schedule.circuit_scheduling == expected_circuit_scheduling))

        # verifies data names and order
        data_names = ["Branch", "Instruction", "Channel", "Start", "Finish", "Pulse", "GateName"]
        for idx, name in enumerate(data_names):
            self.assertEqual(circuit_schedule.type_to_idx[name], idx)

    @ddt.data(
        (None, False, False, 14, 7),
        (("AWGR0_1", "Qubit 0", "Qubit 1", "Hub", "Receive"), False, False, 5, 7),
        (("AWGR0_1", "Qubit 0", "Qubit 1", "Hub", "Receive"), True, False, 4, 7),
        (("AWGR0_1", "Qubit 0", "Qubit 1", "Hub", "Receive"), False, True, 5, 6),
        (("AWGR0_1", "Qubit 0", "Qubit 1", "Hub", "Receive"), True, True, 4, 6),
    )
    @ddt.unpack
    def test_preprocess(
        self,
        included_channels,
        filter_readout_channels,
        filter_barriers,
        n_channels,
        n_instructions,
    ):
        """Test for correct circuit schedule preprocessing"""
        data = self.get_large_mock_data()
        circuit_schedule = CircuitSchedule(data)

        if included_channels is not None:
            included_channels = list(included_channels)

        circuit_schedule.preprocess(
            included_channels=included_channels,
            filter_awgr=filter_readout_channels,
            filter_barriers=filter_barriers,
        )
        self.assertEqual(len(circuit_schedule.channels), n_channels)
        self.assertEqual(len(circuit_schedule.instruction_set), n_instructions)

    def test_get_trace_finite_duration_y_shift(self):
        """Test that x, y, and z shifts for finite duration traces are set correctly"""
        branches = ("main", "then", "else")
        expected_shifts = ((-0.4, 0.4, 0), (0, 0.4, 0.25), (-0.4, 0, -0.25))
        for branch, expected_shift in zip(branches, expected_shifts):
            shifts = CircuitSchedule.get_trace_finite_duration_y_shift(CircuitSchedule, branch)
            self.assertEqual(shifts, expected_shift)

        # test error raise
        with self.assertRaises(ValueError):
            error_branch = "not_a_branch"
            _ = CircuitSchedule.get_trace_finite_duration_y_shift(CircuitSchedule, error_branch)

    def test_get_trace_zero_duration_y_shift(self):
        """Test that y-shift for zero duration traces are set correctly"""
        branches = ("main", "then", "else")
        expected_shifts = (0, 0.2, -0.2)
        for branch, expected_shift in zip(branches, expected_shifts):
            shifts = CircuitSchedule.get_trace_zero_duration_y_shift(CircuitSchedule, branch)
            self.assertEqual(shifts, expected_shift)

        # test error raise
        with self.assertRaises(ValueError):
            error_branch = "not_a_branch"
            _ = CircuitSchedule.get_trace_zero_duration_y_shift(CircuitSchedule, error_branch)

    def test_trace_finite_duration_instruction(self):
        """Test that finite duration traces are created correctly"""
        # initialize a class
        data = self.get_small_mock_data()
        circuit_schedule = CircuitSchedule(data)
        circuit_schedule.preprocess()

        # test a single row schedule
        schedule_row = ["main", "barrier", "Qubit 0", "7", "7", "barrier", "barrier"]
        circuit_schedule.trace_finite_duration_instruction(schedule_row)

        # each row schedule results in one trace and one annotation
        self.assertEqual(len(circuit_schedule.traces), 1)
        self.assertEqual(len(circuit_schedule.annotations), 1)

    def test_trace_zero_duration_instruction(self):
        """Test that shift phase (zero duration) traces are created correctly"""
        # initialize a class
        data = self.get_large_mock_data()
        circuit_schedule = CircuitSchedule(data)
        circuit_schedule.preprocess()

        # test a single row schedule
        schedule_row = [
            "else",
            "sx_2",
            "Qubit 2",
            "2282",
            "2282",
            "shift_phase",
            "sx",
        ]
        circuit_schedule.trace_finite_duration_instruction(schedule_row)

        # each row schedule results in one trace and one annotation
        self.assertEqual(len(circuit_schedule.traces), 1)
        self.assertEqual(len(circuit_schedule.annotations), 1)

    @ddt.data(
        (None, False, False, 104, 7),
        (("AWGR0_1", "Qubit 0", "Qubit 1", "Hub", "Receive"), False, False, 34, 7),
        (("AWGR0_1", "Qubit 0", "Qubit 1", "Hub", "Receive"), True, False, 32, 7),
        (("AWGR0_1", "Qubit 0", "Qubit 1", "Hub", "Receive"), False, True, 26, 6),
        (("AWGR0_1", "Qubit 0", "Qubit 1", "Hub", "Receive"), True, True, 24, 6),
    )
    @ddt.unpack
    def test_populate_figure(
        self, included_channels, filter_readout_channels, filter_barriers, n_traces, n_instructions
    ):
        """Test for making sure the figure is populated correctly"""
        go = plotly_module(".graph_objects")

        data = self.get_large_mock_data()
        circuit_schedule = CircuitSchedule(data)

        if included_channels is not None:
            included_channels = list(included_channels)

        circuit_schedule.preprocess(
            included_channels=included_channels,
            filter_awgr=filter_readout_channels,
            filter_barriers=filter_barriers,
        )

        fig = circuit_schedule.populate_figure(go.Figure())
        self.assertEqual(len(fig.data), n_traces)
        self.assertEqual(len(circuit_schedule.legend), n_instructions)
