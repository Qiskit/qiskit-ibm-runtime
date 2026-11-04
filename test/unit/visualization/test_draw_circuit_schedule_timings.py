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

"""Unit tests for the circuit schedule timing visualization."""

import pytest

from qiskit_ibm_runtime.visualization import draw_circuit_schedule_timing
from qiskit_ibm_runtime.visualization.circuit_schedule import CircuitSchedule

from .utils import save_plotly_artifact


class TestDrawCircuitScheduleTiming:
    """Tests for the ``draw_circuit_schedule_timing`` function."""

    @pytest.mark.parametrize(
        ("included_channels", "filter_readout_channels", "filter_barriers", "expected_n_traces"),
        [
            (None, False, False, 104),
            (("AWGR0_1", "Qubit 0", "Qubit 1", "Hub", "Receive"), False, True, 26),
        ],
    )
    def test_plotting(
        self,
        included_channels: list[str] | None,
        filter_readout_channels: bool,
        filter_barriers: bool,
        expected_n_traces: int,
        test_id: str,
        large_timing: str,
    ) -> None:
        """Test to make sure that it produces the right figure."""
        if included_channels is not None:
            included_channels = list(included_channels)

        # test string input
        fig_1 = draw_circuit_schedule_timing(
            circuit_schedule=large_timing,
            included_channels=included_channels,
            filter_readout_channels=filter_readout_channels,
            filter_barriers=filter_barriers,
        )
        assert len(fig_1.data) == expected_n_traces
        save_plotly_artifact(test_id, fig_1)

        # test class input
        circuit_schedule_object = CircuitSchedule(large_timing)
        fig_2 = draw_circuit_schedule_timing(
            circuit_schedule=circuit_schedule_object,
            included_channels=included_channels,
            filter_readout_channels=filter_readout_channels,
            filter_barriers=filter_barriers,
        )
        assert len(fig_2.data) == expected_n_traces
        save_plotly_artifact(test_id, fig_2)
