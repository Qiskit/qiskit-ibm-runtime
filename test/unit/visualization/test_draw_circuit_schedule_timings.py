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

"""Unit tests for the circuit schedule timing visualization."""

import ddt
from qiskit_ibm_runtime.visualization import draw_circuit_schedule_timing
from qiskit_ibm_runtime.utils.circuit_schedule import CircuitSchedule
from ...ibm_test_case import IBMTestCase
from ..mock.fake_circuit_schedule_timing import FakeCircuitScheduleInputData


@ddt.ddt
class TestDrawCircuitScheduleTiming(IBMTestCase):
    """Tests for the ``draw_circuit_schedule_timing`` function."""

    def setUp(self) -> None:
        """Set up."""
        fake_sampler_pub_result = FakeCircuitScheduleInputData.sampler_pub_result_large
        self.circuit_schedule_data = fake_sampler_pub_result.metadata["compilation"][
            "scheduler_timing"
        ]["timing"]

    def get_mock_data(self):
        """Return the data object"""
        return self.circuit_schedule_data

    @ddt.data(
        (None, False, False, 104),
        (("AWGR0_1", "Qubit 0", "Qubit 1", "Hub", "Receive"), False, True, 26),
    )
    @ddt.unpack
    def test_plotting(
        self, included_channels, filter_readout_channels, filter_barriers, expected_n_traces
    ):
        r"""
        Test to make sure that it produces the right figure.
        """
        circuit_schedule = self.get_mock_data()

        if included_channels is not None:
            included_channels = list(included_channels)

        # test string input
        fig_1 = draw_circuit_schedule_timing(
            circuit_schedule=circuit_schedule,
            included_channels=included_channels,
            filter_readout_channels=filter_readout_channels,
            filter_barriers=filter_barriers,
        )
        self.assertEqual(len(fig_1.data), expected_n_traces)
        self.save_plotly_artifact(fig_1)

        # test class input
        circuit_schedule_object = CircuitSchedule(circuit_schedule)
        fig_2 = draw_circuit_schedule_timing(
            circuit_schedule=circuit_schedule_object,
            included_channels=included_channels,
            filter_readout_channels=filter_readout_channels,
            filter_barriers=filter_barriers,
        )
        self.assertEqual(len(fig_2.data), expected_n_traces)
        self.save_plotly_artifact(fig_2)
