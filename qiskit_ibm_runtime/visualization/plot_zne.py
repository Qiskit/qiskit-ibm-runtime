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

from itertools import product
from plotly.colors import sample_colorscale, diverging
from plotly.subplots import make_subplots
import numpy as np
import plotly.graph_objects as go

from ..utils.estimator_pub_result import EstimatorPubResult


def plot_zne(result: EstimatorPubResult, tol: float = 2.0e-1) -> go.Figure:
    """Plot an :class:`~.EstimatorPubResult` with zero noise extrapolation data.

    Args:
        result: An :class:`~.EstimatorPubResult`.
        tol: The tolerance. If ``stds_extrapolated`` is greater than this value for a expectation value
        and extrapolator, the fit is omitted from the plot.

    Returns:
        A plotly figure.

    Raises:
        ValueError: If ``result`` does not contain zero noise extrapolation data.
    """
    if not (zne_metadata := result.metadata["resilience"].get("zne")):
        raise ValueError("Result does not contain ZNE data.")

    noise_factors = zne_metadata["noise_factors"]
    extrapolated_noise_factors = zne_metadata["extrapolated_noise_factors"]
    extrapolators = zne_metadata["extrapolators"]

    fig = make_subplots(cols=len(extrapolators), subplot_titles=extrapolators)

    # generate the x coordinates for the fill around the fit
    e_nfs_fill = extrapolated_noise_factors + extrapolated_noise_factors[::-1]

    colors = sample_colorscale(diverging.Spectral, np.linspace(0, 1, result.data.size))

    for idx, obs in enumerate(product(*(range(s) for s in result.data.shape))):
        show_legend = True
        color = colors[idx]
        for idx_m in range(len(extrapolators)):
            evs = result.data.evs_extrapolated[obs + (idx_m,)]
            evs_std = result.data.stds_extrapolated[obs + (idx_m,)]
            if any(evs_std > tol):
                continue

            # generate the y coordinates for the fill around the fit
            evs_fill = (evs + evs_std).tolist() + (evs - evs_std).tolist()[::-1]

            fig.add_traces(
                [
                    go.Scatter(
                        x=noise_factors,
                        y=result.data.evs_noise_factors[obs],
                        name=f"evs_{obs if len(obs) != 1 else obs[0]}",
                        mode="markers",
                        marker=dict(color=color),
                        error_y=dict(array=result.data.stds_noise_factors[obs]),
                        legendgroup=idx,
                        showlegend=show_legend,
                    ),
                    go.Scatter(
                        x=extrapolated_noise_factors,
                        y=evs,
                        mode="lines",
                        line=dict(color=color),
                        legendgroup=idx,
                        showlegend=False,
                    ),
                    go.Scatter(
                        x=e_nfs_fill,
                        y=evs_fill,
                        fill="toself",
                        fillcolor=color,
                        line=dict(color="rgba(255,255,255,0)"),
                        opacity=0.2,
                        legendgroup=idx,
                        hoverinfo="skip",
                        showlegend=False,
                    ),
                ],
                rows=1,
                cols=idx_m + 1,
            )
            show_legend = False

    fig.update_yaxes(
        range=[
            np.min(result.data.evs_noise_factors) - 0.5,
            np.max(result.data.evs_noise_factors) + 0.5,
        ],
    )

    return fig
