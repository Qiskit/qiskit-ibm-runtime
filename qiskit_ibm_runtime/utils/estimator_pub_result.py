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

"""
========================================================================================
EstimatorPubResult result classes (:mod:`qiskit_ibm_runtime.utils.estimator_pub_result`)
========================================================================================

.. autosummary::
   :toctree: ../stubs/
"""

from __future__ import annotations

from typing import Sequence, TYPE_CHECKING

from qiskit.primitives.containers import PubResult

if TYPE_CHECKING:
    from plotly.graph_objects import Figure as PlotlyFigure


class EstimatorPubResult(PubResult):
    """Result of Estimator Pub."""

    def draw_zne_evs(
        self,
        indices: Sequence[tuple[int, ...]] | None = None,
        names: Sequence[str] | None = None,
        num_stds: int = 1,
        max_mag: float = 10,
        max_std: float = 0.2,
        height: int = 500,
        width: int = 1000,
        num_cols: int = 4,
        colorscale: str = "Aggrnyl",
    ) -> PlotlyFigure:
        """Plot the zero noise extrapolation data contained in this estimator pub result.

        This method generates a subfigure for each expectation value.

        Args:
            indices: The indices of the expectation values to include in the plot. If ``None``, includes
                all values. See :class:`~.ZneOptions` for information on the indexing scheme.
            names: The names to assign to the expectation values. If ``None``, the names correspond to
                the indices.
            num_stds: The number of standard deviations to include around each fit.
            max_mag: The maximum magnitude of expectation values to include. If ``evs_extrapolated`` has
                a greater magnitude than this value, the expectation value is omitted from the plot.
            max_std: The maximum standard deviation to include. If ``stds_extrapolated`` is greater than
                this value for an expectation value and extrapolator, the fit is omitted from the plot.
            height: The height of the plot in pixels.
            width: The width of the plot in pixels.
            num_cols: The maximum number of columns in the figure.
            colorscale: The colorscale to use.

        Returns:
            A plotly figure.
        """
        # pylint: disable=import-outside-toplevel, cyclic-import
        from ..visualization import draw_zne_evs

        return draw_zne_evs(
            self,
            indices=indices,
            names=names,
            num_stds=num_stds,
            max_mag=max_mag,
            max_std=max_std,
            height=height,
            width=width,
            num_cols=num_cols,
            colorscale=colorscale,
        )

    def draw_zne_extrapolators(
        self,
        indices: Sequence[tuple[int, ...]] | None = None,
        names: Sequence[str] | None = None,
        num_stds: int = 1,
        max_mag: float = 10,
        max_std: float = 0.2,
        height: int = 500,
        width: int = 1000,
        colorscale: str = "Aggrnyl",
    ) -> PlotlyFigure:
        """Plot the zero noise extrapolation data contained in this estimator pub result.

        This method generates a subfigure for each extrapolator.

        Args:
            indices: The indices of the expectation values to include in the plot. If ``None``, includes
                all values. See :class:`~.ZneOptions` for information on the indexing scheme.
            names: The names to assign to the expectation values. If ``None``, the names correspond to
                the indices.
            num_stds: The number of standard deviations to include around each fit.
            max_mag: The maximum magnitude of expectation values to include. If ``evs_extrapolated`` has
                a greater magnitude than this value, the expectation value is omitted from the plot.
            max_std: The maximum standard deviation to include. If ``stds_extrapolated`` is greater than
                this value for an expectation value and extrapolator, the fit is omitted from the plot.
            height: The height of the plot in pixels.
            width: The width of the plot in pixels.
            colorscale: The colorscale to use.

        Returns:
            A plotly figure.
        """
        # pylint: disable=import-outside-toplevel, cyclic-import
        from ..visualization import draw_zne_extrapolators

        return draw_zne_extrapolators(
            self,
            indices=indices,
            names=names,
            num_stds=num_stds,
            max_mag=max_mag,
            max_std=max_std,
            height=height,
            width=width,
            colorscale=colorscale,
        )
