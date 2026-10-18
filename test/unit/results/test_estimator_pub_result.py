# This code is part of Qiskit.
#
# (C) Copyright IBM 2024-2026.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Tests for the classes used to instantiate estimator pub results."""

import numpy as np
import pytest
from qiskit.primitives import DataBin

from qiskit_ibm_runtime.results.estimator_pub import EstimatorPubResult

try:
    import plotly.graph_objects as go

    PLOTLY_INSTALLED = True
except ImportError:
    PLOTLY_INSTALLED = False


@pytest.fixture
def zne_pub_result() -> EstimatorPubResult:
    """Return a pub result holding ZNE data for two noise factors and one extrapolator."""
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

    return EstimatorPubResult(data, metadata)


class TestEstimatorPubResult:
    """Class for testing the EstimatorPubResult class."""

    @pytest.mark.skipif(not PLOTLY_INSTALLED, reason="Plotly is not installed")
    def test_plot_zne(self, zne_pub_result: EstimatorPubResult) -> None:
        """Test that plots are generated with each method."""
        fig = zne_pub_result.draw_zne_evs()
        assert isinstance(fig, go.Figure)

        fig = zne_pub_result.draw_zne_extrapolators()
        assert isinstance(fig, go.Figure)

    @pytest.mark.skipif(not PLOTLY_INSTALLED, reason="Plotly is not installed")
    def test_plot_zne_raises(self) -> None:
        """Test the raises."""
        with pytest.raises(ValueError):
            EstimatorPubResult(DataBin()).draw_zne_evs()

        with pytest.raises(ValueError):
            EstimatorPubResult(DataBin(), {"resilience": {"measure_mitigation": ""}}).draw_zne_evs()

        with pytest.raises(ValueError):
            EstimatorPubResult(
                DataBin(), {"resilience": {"zne": {"noise_factors": [1]}}}
            ).draw_zne_evs(names=["test"])
