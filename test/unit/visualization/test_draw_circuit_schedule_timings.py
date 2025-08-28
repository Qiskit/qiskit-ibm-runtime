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

"""Unit tests for the circuit schedule timing class and visualization."""



from qiskit_ibm_runtime.visualization import draw_circuit_schedule_timing
from qiskit_ibm_runtime.utils.circuit_schedule import CircuitSchedule

from ...ibm_test_case import IBMTestCase
import numpy as np

import time


class DrawCircuitScheduleBase(IBMTestCase):
    """Circuit schedule timing mock data for testing."""
    def setUp(self) -> None:
        """Set up."""
        self.circuit_schedule_data = [
            "main,barrier,Qubit 0,7,0,barrier",
            "main,barrier,Qubit 1,7,0,barrier",
            "main,barrier,Qubit 2,7,0,barrier",
            "main,barrier,Qubit 3,7,0,barrier",
            "main,barrier,Qubit 4,7,0,barrier",
            "main,barrier,Qubit 5,7,0,barrier",
            "main,reset_0,Qubit 0,7,64,play",
            "main,reset_0,Qubit 0,71,108,play",
            "main,reset_0,AWGR0_0,118,325,capture",
            "main,reset_0,Qubit 0,179,64,play",
            "main,reset_0,Qubit 0,243,64,play",
            "main,reset_0,Qubit 0,577,8,play",
            "main,reset_1,Qubit 1,7,64,play",
            "main,reset_1,Qubit 1,71,108,play",
            "main,reset_1,AWGR0_1,118,325,capture",
            "main,reset_1,Qubit 1,179,64,play",
            "main,reset_1,Qubit 1,243,64,play",
            "main,reset_1,Qubit 1,577,8,play",
            "main,reset_2,Qubit 2,7,64,play",
            "main,reset_2,Qubit 2,71,108,play",
            "main,reset_2,AWGR0_2,118,325,capture",
            "main,reset_2,Qubit 2,179,64,play",
            "main,reset_2,Qubit 2,243,64,play",
            "main,reset_2,Qubit 2,577,8,play",
            "main,reset_3,Qubit 3,7,64,play",
            "main,reset_3,Qubit 3,71,108,play",
            "main,reset_3,AWGR0_3,118,325,capture",
            "main,reset_3,Qubit 3,179,64,play",
            "main,reset_3,Qubit 3,243,64,play",
            "main,reset_3,Qubit 3,577,8,play",
            "main,reset_4,Qubit 4,7,64,play",
            "main,reset_4,Qubit 4,71,108,play",
            "main,reset_4,AWGR1_0,118,325,capture",
            "main,reset_4,Qubit 4,179,64,play",
            "main,reset_4,Qubit 4,243,64,play",
            "main,reset_4,Qubit 4,577,8,play",
            "main,reset_5,Qubit 5,7,64,play",
            "main,reset_5,Qubit 5,71,108,play",
            "main,reset_5,AWGR1_1,118,325,capture",
            "main,reset_5,Qubit 5,179,64,play",
            "main,reset_5,Qubit 5,243,64,play",
            "main,reset_5,Qubit 5,577,8,play",
            "main,barrier,Qubit 0,585,0,barrier",
            "main,barrier,Qubit 1,585,0,barrier",
            "main,barrier,Qubit 2,585,0,barrier",
            "main,barrier,Qubit 3,585,0,barrier",
            "main,barrier,Qubit 4,585,0,barrier",
            "main,barrier,Qubit 5,585,0,barrier",
            "main,x_0,Qubit 0,585,8,play",
            "main,x_2,Qubit 2,585,8,play",
            "main,x_4,Qubit 4,585,8,play",
            "main,barrier,Qubit 0,593,0,barrier",
            "main,barrier,Qubit 2,593,0,barrier",
            "main,barrier,Qubit 4,593,0,barrier",
            "main,measure_0,Qubit 0,593,64,play",
            "main,measure_0,Qubit 0,657,108,play",
            "main,measure_0,AWGR0_0,704,325,capture",
            "main,measure_0,Qubit 0,765,64,play",
            "main,measure_0,Qubit 0,829,64,play",
            "main,measure_2,Qubit 2,593,64,play",
            "main,measure_2,Qubit 2,657,108,play",
            "main,measure_2,AWGR0_2,704,325,capture",
            "main,measure_2,Qubit 2,765,64,play",
            "main,measure_2,Qubit 2,829,64,play",
            "main,measure_4,Qubit 4,593,64,play",
            "main,measure_4,Qubit 4,657,108,play",
            "main,measure_4,AWGR1_0,704,325,capture",
            "main,measure_4,Qubit 4,765,64,play",
            "main,measure_4,Qubit 4,829,64,play",
            "main,barrier,Qubit 0,1668,0,barrier",
            "main,barrier,Qubit 2,1668,0,barrier",
            "main,barrier,Qubit 4,1668,0,barrier",
            "main,broadcast,Hub,704,964,broadcast",
            "main,receive,Receive,1668,7,receive",
            "then,x_1,Qubit 1,1695,8,play",
            "else,sx_0,Qubit 0,1699,8,play",
            "else,sx_0,Qubit 0,1707,0,shift_phase",
            "main,x_3,Qubit 3,1704,8,play",
            "main,x_5,Qubit 5,1704,8,play",
            "main,barrier,Qubit 1,1712,0,barrier",
            "main,barrier,Qubit 3,1712,0,barrier",
            "main,barrier,Qubit 5,1712,0,barrier",
            "main,measure_1,Qubit 1,1712,64,play",
            "main,measure_1,Qubit 1,1776,108,play",
            "main,measure_1,AWGR0_1,1823,325,capture",
            "main,measure_1,Qubit 1,1884,64,play",
            "main,measure_1,Qubit 1,1948,64,play",
            "main,measure_3,Qubit 3,1712,64,play",
            "main,measure_3,Qubit 3,1776,108,play",
            "main,measure_3,AWGR0_3,1823,325,capture",
            "main,measure_3,Qubit 3,1884,64,play",
            "main,measure_3,Qubit 3,1948,64,play",
            "main,measure_5,Qubit 5,1712,64,play",
            "main,measure_5,Qubit 5,1776,108,play",
            "main,measure_5,AWGR1_1,1823,325,capture",
            "main,measure_5,Qubit 5,1884,64,play",
            "main,measure_5,Qubit 5,1948,64,play",
            "main,barrier,Qubit 1,2282,0,barrier",
            "main,barrier,Qubit 3,2282,0,barrier",
            "main,barrier,Qubit 5,2282,0,barrier",
            "else,sx_2,Qubit 2,2274,8,play",
            "else,sx_2,Qubit 2,2282,0,shift_phase",
            "else,sx_4,Qubit 4,2274,8,play",
            "else,sx_4,Qubit 4,2282,0,shift_phase",
        ]
        self.small_data_len = 5
        # test cases structure:
        #   --------------------   Input Arguments   ------------------       ----------    Expected Results    ---------
        # ((included_channels, filter_readout_channels, filter_barriers)  ,  (n_traces, n_channels, n_unique_instructions))
        self.test_cases = {
            1: ((None, False, False), (104, 14, 7)),
            2: ((["AWGR0_1", "Qubit 0", "Qubit 1", "Hub", "Receive"], False, False), (34, 5, 7)),
            3: ((["AWGR0_1", "Qubit 0", "Qubit 1", "Hub", "Receive"], True, False), (32, 4, 7)),
            4: ((["AWGR0_1", "Qubit 0", "Qubit 1", "Hub", "Receive"], False, True), (26, 4, 6)),
            5: ((["AWGR0_1", "Qubit 0", "Qubit 1", "Hub", "Receive"], True, True), (24, 4, 6)),
        }
    def get_large_mock_data(self):
        return self.circuit_schedule_data
    
    def get_small_mock_data(self):
        return self.circuit_schedule_data[:self.small_data_len]
    




class TestCircuitSchedule(DrawCircuitScheduleBase):
    """Tests for CircuitSchedule class."""

    def test__load(self):
        data = self.get_small_mock_data()
        loaded_data = CircuitSchedule._load(data)
        self.assertEqual(data, loaded_data)
        # TODO: should we also add a test for file loading?

    def test__parse(self):
        data = self.get_small_mock_data()
        circuit_schedule = CircuitSchedule(data)
        self.assertIsNotNone(circuit_schedule.circuit_scheduling)

        expected_circuit_scheduling = [
            ['main', 'barrier', 'Qubit 0', '7', '7', 'barrier', 'barrier'],
            ['main', 'barrier', 'Qubit 1', '7', '7', 'barrier', 'barrier'],
            ['main', 'barrier', 'Qubit 2', '7', '7', 'barrier', 'barrier'],
            ['main', 'barrier', 'Qubit 3', '7', '7', 'barrier', 'barrier'],
            ['main', 'barrier', 'Qubit 4', '7', '7', 'barrier', 'barrier'],
            ]
        self.assertTrue(np.all(circuit_schedule.circuit_scheduling==expected_circuit_scheduling))

        # tests that empty data lines are ignored in parsing
        data_extended = data + [""]
        self.assertEqual(len(data) + 1, len(data_extended))
        circuit_schedule = CircuitSchedule(data)
        self.assertIsNotNone(circuit_schedule.circuit_scheduling)
        self.assertTrue(np.all(circuit_schedule.circuit_scheduling==expected_circuit_scheduling))

        # verifies data names and order
        data_names = ["Branch", "Instruction", "Channel", "Start", "Finish", "Pulse", "GateName"]
        for idx, name in enumerate(data_names):
            self.assertEqual(circuit_schedule.type_to_idx[name], idx)

    def test_preprocess(self):
        data = self.get_large_mock_data()
        circuit_schedule = CircuitSchedule(data)

        for _, test_case in self.test_cases.items():
            (
                (included_channels, filter_readout_channels, filter_barriers), 
                (n_traces, n_channels, n_instructions)
                ) = test_case
            circuit_schedule.preprocess(
                included_channels=included_channels, 
                filter_awgr=filter_readout_channels, 
                filter_barriers=filter_barriers
                )
            self.assertEqual(len(circuit_schedule.channels), n_channels)
            self.assertEqual(len(circuit_schedule.instruction_set), n_instructions)

    def test_get_trace_finite_duration_y_shift(self):
        branches = ("main", "then", "else")
        expected_shifts = ((-0.4, 0.4, 0), (0, 0.4, 0.25), (-0.4, 0, -0.25))
        for branch, expected_shift in zip(branches, expected_shifts):
            shifts = CircuitSchedule.get_trace_finite_duration_y_shift(CircuitSchedule, branch)
            self.assertEqual(shifts, expected_shift)
        
        # test error raise
        with self.assertRaises(ValueError):
            error_branch = "some_branch"
            _ = CircuitSchedule.get_trace_finite_duration_y_shift(CircuitSchedule, error_branch)

    def test_get_trace_zero_duration_y_shift(self):
        branches = ("main", "then", "else")
        expected_shifts = (0, 0.2, -0.2)
        for branch, expected_shift in zip(branches, expected_shifts):
            shifts = CircuitSchedule.get_trace_zero_duration_y_shift(CircuitSchedule, branch)
            self.assertEqual(shifts, expected_shift)
        
        # test error raise
        with self.assertRaises(ValueError):
            error_branch = "some_branch"
            _ = CircuitSchedule.get_trace_zero_duration_y_shift(CircuitSchedule, error_branch)

    def test_trace_finite_duration_instruction(self):
        pass

    def test_trace_zero_duration_instruction(self):
        pass

    def test_populate_figure(self):
        pass


class TestDrawCircuitScheduleTiming(DrawCircuitScheduleBase):
    """Tests for the ``draw_circuit_schedule_timing`` function."""

    def test_plotting(self):
        r"""
        Test to make sure that it produces the right figure.
        """
        
        circuit_schedule = self.get_large_mock_data()
        for _, test_case in self.test_cases.items():
            (
                (included_channels, filter_readout_channels, filter_barriers), 
                (n_traces, _, _)
                ) = test_case
            fig = draw_circuit_schedule_timing(
                circuit_schedule=circuit_schedule,
                included_channels=included_channels,
                filter_readout_channels=filter_readout_channels,
                filter_barriers=filter_barriers,
                )
            self.assertEqual(len(fig.data), n_traces)

            # TODO: remove this
            fig.write_html("downloads/temp-plot2.html", auto_open=True)
            time.sleep(0.5)

        self.save_plotly_artifact(fig)
