# This code is part of Qiskit.
#
# (C) Copyright IBM 2024.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Tests for the classes used to instantiate estimator pub results."""

from unittest import skipIf
import numpy as np

from qiskit.primitives import DataBin

from qiskit_ibm_runtime.utils.estimator_pub_result import EstimatorPubResult

from ..ibm_test_case import IBMTestCase

try:
    import plotly.graph_objects as go

    PLOTLY_INSTALLED = True
except ImportError:
    PLOTLY_INSTALLED = False


class TestEstimatorPubResult(IBMTestCase):
    """Class for testing the EstimatorPubResult class."""

    def setUp(self):
        super().setUp()

        nfs = np.zeros((2, 2))
        extrapolated = np.zeros((2, 2, 3))
        data = DataBin(
            shape=(2,),
            evs_noise_factors=nfs,
            stds_noise_factors=nfs,
            evs_extrapolated=extrapolated,
            stds_extrapolated=extrapolated,
        )

        metadata = {
            "resilience": {
                "zne": {
                    "extrapolators": ["linear"],
                    "extrapolated_noise_factors": [0, 2, 3],
                    "noise_factors": [2, 3],
                }
            }
        }

        self.pub_result = EstimatorPubResult(data, metadata)

    @skipIf(not PLOTLY_INSTALLED, reason="Plotly is not installed")
    def test_plot_zne(self):
        """Test that plots are generated with each method."""
        fig = self.pub_result.draw_zne_evs()
        self.assertIsInstance(fig, go.Figure)

        fig = self.pub_result.draw_zne_extrapolators()
        self.assertIsInstance(fig, go.Figure)

    @skipIf(not PLOTLY_INSTALLED, reason="Plotly is not installed")
    def test_plot_zne_raises(self):
        """Test the raises."""
        with self.assertRaises(ValueError):
            EstimatorPubResult(DataBin()).draw_zne_evs()

        with self.assertRaises(ValueError):
            EstimatorPubResult(DataBin(), {"resilience": {"measure_mitigation": ""}}).draw_zne_evs()

        with self.assertRaises(ValueError):
            EstimatorPubResult(
                DataBin(), {"resilience": {"zne": {"noise_factors": [1]}}}
            ).draw_zne_evs(names=["test"])
