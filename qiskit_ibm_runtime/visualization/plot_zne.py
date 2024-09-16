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

from typing import TYPE_CHECKING

from plotly.colors import DEFAULT_PLOTLY_COLORS
from plotly.subplots import make_subplots
import plotly.graph_objects as go

from qiskit.primitives.containers import PubResult

from ..options.zne_options import ExtrapolatorType


def plot_zne(
    result: PubResult,
    extrapolated_noise_factors: list[int],
    models: list[ExtrapolatorType],
) -> go.Figure:
    if not result.metadata["resilience"].get("zne"):
        raise ValueError("Result does not contain ZNE data.")

    nfs_fill = extrapolated_noise_factors + extrapolated_noise_factors[::-1]

    shape = (-1, len(extrapolated_noise_factors), len(models))
    evs_reshaped = result.data.evs_extrapolated.reshape(shape)
    evs_std_reshaped = result.data.stds_extrapolated.reshape(shape)

    fig = make_subplots(cols=len(models), subplot_titles=models)

    for idx in range(result.data.size):
        show_legend = True
        for idx_m in range(len(models)):
            evs = evs_reshaped[(idx, idx_m)]
            evs_std = evs_std_reshaped[(idx, idx_m)]
            evs_fill_up = (evs + evs_std).tolist()
            evs_fill_down = (evs - evs_std).tolist()

            fig.add_traces(
                [
                    go.Scatter(
                        x=extrapolated_noise_factors,
                        y=evs,
                        name=f"observable_{idx}",
                        marker=dict(color=DEFAULT_PLOTLY_COLORS[idx]),
                        error_y=dict(array=evs_std),
                        legendgroup=idx,
                        showlegend=show_legend,
                    ),
                    go.Scatter(
                        x=nfs_fill,
                        y=evs_fill_up + evs_fill_down[::-1],  # upper, then lower reversed
                        fill="toself",
                        fillcolor=DEFAULT_PLOTLY_COLORS[idx],
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

    return fig
