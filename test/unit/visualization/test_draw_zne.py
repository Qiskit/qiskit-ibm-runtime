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

"""Tests for the functions used to visualize ZNE expectation values."""

import numpy as np
from qiskit.primitives.containers import DataBin

from qiskit_ibm_runtime.results.estimator_pub import EstimatorPubResult
from qiskit_ibm_runtime.visualization import draw_zne_evs, draw_zne_extrapolators

from ...ibm_test_case import IBMTestCase
from .utils import save_plotly_artifact


def zne_results():
    """Return a pub result holding ZNE data, and pub results missing that data."""
    data = DataBin(
        shape=(1,),
        evs=np.ones((1,)),
        stds=np.zeros((1,)),
        evs_noise_factors=np.ones((1, 3)),
        stds_noise_factors=np.zeros((1, 3)),
        ensemble_stds_noise_factors=np.zeros((1, 3)),
        evs_extrapolated=np.ones((1, 2, 4)),
        stds_extrapolated=np.zeros((1, 2, 4)),
    )
    metadata = {
        "resilience": {
            "zne": {
                "noise_factors": [1, 3, 5],
                "extrapolated_noise_factors": [0, 1, 3, 5],
                "extrapolators": ["exponential", "linear"],
            }
        }
    }

    zne_data = EstimatorPubResult(data, metadata)
    error_data = [
        EstimatorPubResult(data),
        EstimatorPubResult(data, metadata={"resilience": {}}),
    ]

    return zne_data, error_data


class TestDrawZNE(IBMTestCase):
    """Class for testing the ``draw_zne_evs`` function."""

    def test_plotting(self):
        """Test to make sure that it produces the right figure."""
        zne_data, _ = zne_results()
        fig = draw_zne_evs(zne_data)

        # 1 expectation value with 2 extrapolators each with 1 std is
        # 1 + 2 * 2 = 5 traces
        assert len(fig.data) == 5
        save_plotly_artifact(self.id(), fig)

    def test_errors(self):
        """Test error when no ZNE data is present."""
        _, error_data = zne_results()
        for error in error_data:
            with self.assertRaises(ValueError):
                draw_zne_evs(error)


class TestDrawZNEExtrapolators(IBMTestCase):
    """Class for testing the ``draw_zne_extrapolators`` function."""

    def test_plotting(self):
        """Test to make sure that it produces the right figure."""
        zne_data, _ = zne_results()
        fig = draw_zne_extrapolators(zne_data)

        # 2 figures (one per extrapolator) with 3 traces each is 6
        assert len(fig.data) == 6
        save_plotly_artifact(self.id(), fig)

    def test_errors(self):
        """Test error when no ZNE data is present."""
        _, error_data = zne_results()
        for error in error_data:
            with self.assertRaises(ValueError):
                draw_zne_extrapolators(error)
