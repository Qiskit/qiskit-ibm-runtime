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

"""Unit tests for the circuit schedule class."""

import numpy as np
import pytest

from qiskit_ibm_runtime.visualization.circuit_schedule import CircuitSchedule
from qiskit_ibm_runtime.visualization.utils import plotly_module

from ..mock.fake_circuit_schedule_timing import FakeCircuitScheduleInputData


@pytest.fixture
def large_timing() -> str:
    """Return the whole scheduler timing of the fake sampler pub results."""
    pub_result = FakeCircuitScheduleInputData.sampler_pub_result_large
    return pub_result.metadata["compilation"]["scheduler_timing"]["timing"]


@pytest.fixture
def small_timing() -> str:
    """Return a small constant portion of the scheduler timing."""
    pub_result = FakeCircuitScheduleInputData.sampler_pub_result_small
    return pub_result.metadata["compilation"]["scheduler_timing"]["timing"]


@pytest.fixture
def merge_timing() -> str:
    """Return the scheduler timing of a merge use case."""
    pub_result = FakeCircuitScheduleInputData.sampler_pub_result_merge
    return pub_result.metadata["compilation"]["scheduler_timing"]["timing"]


class TestCircuitSchedule:
    """Tests for CircuitSchedule class."""

    def test__load(self, small_timing: str) -> None:
        """Test small_timing loading."""
        loaded_data = CircuitSchedule._load(small_timing)
        expected_loaded_data = small_timing.split("\n")
        assert loaded_data == expected_loaded_data

    def test__parse(self, small_timing: str) -> None:
        """Test circuit schedule small_timing parsing."""
        circuit_schedule = CircuitSchedule(small_timing)
        assert circuit_schedule.circuit_scheduling is not None

        expected_circuit_scheduling = [
            ["main", "barrier", "Qubit 0", "7", "7", "barrier", "barrier"],
            ["main", "barrier", "Qubit 1", "7", "7", "barrier", "barrier"],
            ["main", "barrier", "Qubit 2", "7", "7", "barrier", "barrier"],
            ["main", "barrier", "Qubit 3", "7", "7", "barrier", "barrier"],
            ["main", "barrier", "Qubit 4", "7", "7", "barrier", "barrier"],
        ]
        assert np.all(circuit_schedule.circuit_scheduling == expected_circuit_scheduling)

        circuit_schedule = CircuitSchedule(small_timing)
        assert circuit_schedule.circuit_scheduling is not None
        assert np.all(circuit_schedule.circuit_scheduling == expected_circuit_scheduling)

        # verifies small_timing names and order
        data_names = ["Branch", "Instruction", "Channel", "Start", "Finish", "Pulse", "GateName"]
        for idx, name in enumerate(data_names):
            assert circuit_schedule.type_to_idx[name] == idx

    @pytest.mark.parametrize(
        (
            "included_channels",
            "filter_readout_channels",
            "filter_barriers",
            "n_channels",
            "n_instructions",
            "top_channel",
        ),
        [
            (None, False, False, 14, 7, None),
            (("AWGR0_1", "Qubit 0", "Qubit 1", "Hub", "Receive"), False, False, 5, 7, "AWGR0_1"),
            (("AWGR0_1", "Qubit 0", "Qubit 1", "Hub", "Receive"), True, False, 4, 7, "Qubit 0"),
            (("AWGR0_1", "Qubit 0", "Qubit 1", "Hub", "Receive"), False, True, 5, 6, "AWGR0_1"),
            (("AWGR0_1", "Qubit 0", "Qubit 1", "Hub", "Receive"), True, True, 4, 6, "Qubit 0"),
            (("Hub", "AWGR0_1", "Qubit 0", "Qubit 1", "Receive"), True, True, 4, 6, "Hub"),
        ],
    )
    def test_preprocess(
        self,
        included_channels: list[str] | None,
        filter_readout_channels: bool,
        filter_barriers: bool,
        n_channels: int,
        n_instructions: int,
        top_channel: str | None,
        large_timing: str,
    ) -> None:
        """Test for correct circuit schedule preprocessing."""
        circuit_schedule = CircuitSchedule(large_timing)

        if included_channels is not None:
            included_channels = list(included_channels)

        circuit_schedule.preprocess(
            included_channels=included_channels,
            filter_awgr=filter_readout_channels,
            filter_barriers=filter_barriers,
        )
        assert len(circuit_schedule.channels) == n_channels
        assert len(circuit_schedule.instruction_set) == n_instructions

        if top_channel is not None:
            assert circuit_schedule.channels[-1] == top_channel

    @pytest.mark.parametrize(
        ("to_merge_instruction", "n_instructions"),
        [
            (False, 6),
            (True, 3),
        ],
    )
    def test_merge_common_instructions(
        self, to_merge_instruction: bool, n_instructions: int, merge_timing: str
    ) -> None:
        """Test for instructions merging."""
        circuit_schedule = CircuitSchedule(merge_timing)

        circuit_schedule.preprocess(
            included_channels=None,
            filter_awgr=False,
            filter_barriers=False,
            merge_common_instructions=to_merge_instruction,
        )
        assert len(circuit_schedule.circuit_scheduling) == n_instructions

    def test_get_trace_finite_duration_y_shift(self) -> None:
        """Test that x, y, and z shifts for finite duration traces are set correctly."""
        branches = ("main", "then", "else")
        expected_shifts = ((-0.4, 0.4, 0), (0, 0.4, 0.25), (-0.4, 0, -0.25))
        for branch, expected_shift in zip(branches, expected_shifts):
            shifts = CircuitSchedule("").get_trace_finite_duration_y_shift(branch)
            assert shifts == expected_shift

        # test error raise
        with pytest.raises(ValueError):
            error_branch = "not_a_branch"
            _ = CircuitSchedule("").get_trace_finite_duration_y_shift(error_branch)

    def test_get_trace_zero_duration_y_shift(self) -> None:
        """Test that y-shift for zero duration traces are set correctly."""
        branches = ("main", "then", "else")
        expected_shifts = (0, 0.2, -0.2)
        for branch, expected_shift in zip(branches, expected_shifts):
            shifts = CircuitSchedule("").get_trace_zero_duration_y_shift(branch)
            assert shifts == expected_shift

        # test error raise
        with pytest.raises(ValueError):
            error_branch = "not_a_branch"
            _ = CircuitSchedule("").get_trace_zero_duration_y_shift(error_branch)

    def test_trace_finite_duration_instruction(self, small_timing: str) -> None:
        """Test that finite duration traces are created correctly."""
        # initialize a class
        circuit_schedule = CircuitSchedule(small_timing)
        circuit_schedule.preprocess()

        # test a single row schedule
        schedule_row = ["main", "barrier", "Qubit 0", "7", "7", "barrier", "barrier"]
        circuit_schedule.trace_finite_duration_instruction(schedule_row)  # type: ignore[arg-type]

        # each row schedule results in one trace and one annotation
        assert len(circuit_schedule.traces) == 1
        assert len(circuit_schedule.annotations) == 1

    def test_trace_zero_duration_instruction(self, large_timing: str) -> None:
        """Test that shift phase (zero duration) traces are created correctly."""
        # initialize a class
        circuit_schedule = CircuitSchedule(large_timing)
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
        circuit_schedule.trace_finite_duration_instruction(schedule_row)  # type: ignore[arg-type]

        # each row schedule results in one trace and one annotation
        assert len(circuit_schedule.traces) == 1
        assert len(circuit_schedule.annotations) == 1

    @pytest.mark.parametrize(
        (
            "included_channels",
            "filter_readout_channels",
            "filter_barriers",
            "n_traces",
            "n_instructions",
        ),
        [
            (None, False, False, 104, 7),
            (("AWGR0_1", "Qubit 0", "Qubit 1", "Hub", "Receive"), False, False, 34, 7),
            (("AWGR0_1", "Qubit 0", "Qubit 1", "Hub", "Receive"), True, False, 32, 7),
            (("AWGR0_1", "Qubit 0", "Qubit 1", "Hub", "Receive"), False, True, 26, 6),
            (("AWGR0_1", "Qubit 0", "Qubit 1", "Hub", "Receive"), True, True, 24, 6),
        ],
    )
    def test_populate_figure(
        self,
        included_channels,
        filter_readout_channels,
        filter_barriers,
        n_traces,
        n_instructions,
        large_timing,
    ):
        """Test for making sure the figure is populated correctly."""
        go = plotly_module(".graph_objects")
        circuit_schedule = CircuitSchedule(large_timing)

        if included_channels is not None:
            included_channels = list(included_channels)

        circuit_schedule.preprocess(
            included_channels=included_channels,
            filter_awgr=filter_readout_channels,
            filter_barriers=filter_barriers,
        )

        fig = circuit_schedule.populate_figure(go.Figure())
        assert len(fig.data) == n_traces
        assert len(circuit_schedule.legend) == n_instructions
