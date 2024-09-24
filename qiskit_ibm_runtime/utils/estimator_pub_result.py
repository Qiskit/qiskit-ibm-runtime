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

from typing import Sequence
import plotly.graph_objects as go

from qiskit.primitives.containers import ObservablesArrayLike, PubResult


class EstimatorPubResult(PubResult):
    """Result of Estimator Pub."""

    def plot_zne(
        self,
        indices: Sequence[tuple[int, ...]] | None = None,
        names: Sequence[str] | None = None,
        n_stds: int = 1,
        mag_tol: float = 10,
        std_tol: float = 2e-1,
        height: int = 500,
        width: int = 1000,
        n_cols: int = 5,
        subplots: bool = False,
    ) -> go.Figure:
        """Plot the zero noise extrapolation data contained in this estimator pub result.

        Args:
            indices: The indices of the expectation values to include in the plot. If ``None``, includes all
                values. See :class:`~.ZneOptions` for information on the indexing scheme.
            names: The names to assign to the expectation values. If ``None``, the names correspond to the
                indices.
            n_stds: The number of standard deviations to include around each fit.
            mag_tol: The tolerance.
            std_tol: The tolerance. If ``stds_extrapolated`` is greater than this value for an expectation value
                and extrapolator, the fit is omitted from the plot.
            height: The height of the plot in pixels.
            width: The width of the plot in pixels.
            n_cols: The maximum number of columns in the figure.
            subplots: If ``True``, each expectation value is placed in its own subplot. Otherwise, plot all estimates
                that use the same extrapolator on one plot.
            Returns:
                A plotly figure.
        """
        # pylint: disable=import-outside-toplevel, cyclic-import
        from ..visualization import plot_zne

        return plot_zne(self, indices, names, n_stds, mag_tol, std_tol, height, width, n_cols, subplots)
