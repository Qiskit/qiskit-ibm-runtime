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

    @skipIf(not PLOTLY_INSTALLED, reason="Plotly is not installed")
    def test_plot_zne_no_data(self):
        with self.assertRaises(ValueError):
            EstimatorPubResult(DataBin()).plot_zne()