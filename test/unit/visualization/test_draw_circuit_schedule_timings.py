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


from qiskit_ibm_runtime.visualization import draw_circuit_schedule_timing
from ...ibm_test_case import IBMTestCase
from ..mock.fake_circuit_schedule_timing import FakeCircuitScheduleInputData


class DrawCircuitScheduleBase(IBMTestCase):
    """Circuit schedule timing mock data for testing."""

    def setUp(self) -> None:
        """Set up."""
        self.circuit_schedule_data = FakeCircuitScheduleInputData.data

        # test cases structure:
        #   --------------------   Input Arguments   ------------------       ---  Expected Results  ---
        # ((included_channels, filter_readout_channels, filter_barriers)     ,     (n_traces))
        self.test_cases = {
            1: ((None, False, False), (104)),
        }

    def get_mock_data(self):
        """Return the data object"""
        return self.circuit_schedule_data


class TestDrawCircuitScheduleTiming(DrawCircuitScheduleBase):
    """Tests for the ``draw_circuit_schedule_timing`` function."""

    def test_plotting(self):
        r"""
        Test to make sure that it produces the right figure.
        """
        circuit_schedule = self.get_mock_data()
        for _, test_case in self.test_cases.items():
            ((included_channels, filter_readout_channels, filter_barriers), (n_traces)) = test_case
            fig = draw_circuit_schedule_timing(
                circuit_schedule=circuit_schedule,
                included_channels=included_channels,
                filter_readout_channels=filter_readout_channels,
                filter_barriers=filter_barriers,
                )
            self.assertEqual(len(fig.data), n_traces)
        self.save_plotly_artifact(fig)
