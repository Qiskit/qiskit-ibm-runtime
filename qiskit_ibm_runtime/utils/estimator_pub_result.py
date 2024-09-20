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

from __future__ import annotations

import plotly.graph_objects as go

from qiskit.primitives.containers import ObservablesArrayLike, PubResult

class EstimatorPubResult(PubResult):
    """Result of Estimator Pub."""

    def plot_zne(self, tol: float = 2e-1) -> go.Figure:
        """Plot the zero noise extrapolation data contained in this estimator pub result.

        Args:
            tol: The tolerance. If ``stds_extrapolated`` is greater than this value for a expectation value and extrapolator, the fit is omitted from the plot.

        Returns:
            A plotly figure.
        """
        # pylint: disable=import-outside-toplevel, cyclic-import
        from ..visualization import plot_zne

        return plot_zne(self, tol)
