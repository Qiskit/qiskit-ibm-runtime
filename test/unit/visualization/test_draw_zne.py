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

"""Tests for the functions used to visualize ZNE expectation values."""

import numpy as np

from qiskit.primitives.containers import DataBin

from qiskit_ibm_runtime.visualization import draw_zne_evs, draw_zne_extrapolators
from qiskit_ibm_runtime.utils.estimator_pub_result import EstimatorPubResult

from ...ibm_test_case import IBMTestCase


class DrawZNEBase(IBMTestCase):
    """Base class for testing the functions that visualize ZNE expectation values."""

    def setUp(self):
        super().setUp()
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

        self.zne_data = EstimatorPubResult(data, metadata)
        self.error_data = [
            EstimatorPubResult(data),
            EstimatorPubResult(data, metadata={"resilience": {}}),
        ]


class TestDrawZNE(DrawZNEBase):
    """Class for testing the ``draw_zne_evs`` function."""

    def test_plotting(self):
        r"""
        Test to make sure that it produces the right figure.
        """
        fig = draw_zne_evs(self.zne_data)

        # 1 expectation value with 2 extrapolators each with 1 std is
        # 1 + 2 * 2 = 5 traces
        self.assertEqual(len(fig.data), 5)
        self.save_plotly_artifact(fig)

    def test_errors(self):
        r"""
        Test error when no ZNE data is present.
        """
        for error in self.error_data:
            with self.assertRaises(ValueError):
                draw_zne_evs(error)


class TestDrawZNEExtrapolators(DrawZNEBase):
    """Class for testing the ``draw_zne_extrapolators`` function."""

    def test_plotting(self):
        r"""
        Test to make sure that it produces the right figure.
        """
        fig = draw_zne_extrapolators(self.zne_data)

        # 2 figures (one per extrapolator) with 3 traces each is 6
        self.assertEqual(len(fig.data), 6)
        self.save_plotly_artifact(fig)

    def test_errors(self):
        r"""
        Test error when no ZNE data is present.
        """
        for error in self.error_data:
            with self.assertRaises(ValueError):
                draw_zne_extrapolators(error)
