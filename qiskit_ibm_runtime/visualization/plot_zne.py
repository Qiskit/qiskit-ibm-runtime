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

from itertools import product
from plotly.colors import sample_colorscale, diverging
from plotly.subplots import make_subplots
from typing import Sequence
import numpy as np
import plotly.graph_objects as go

from ..utils.estimator_pub_result import EstimatorPubResult


def plot_zne(
    result: EstimatorPubResult,
    indices: Sequence[tuple[int, ...]] | None = None,
    names: Sequence[str] | None = None,
    n_stds: int = 1,
    mag_tol: float = 10,
    std_tol: float = 2.0e-1,
    height: int = 500,
    width: int = 1000,
    n_cols: int = 5,
    subplots: bool = False,
) -> go.Figure:
    """Plot the zero noise extrapolation data in an :class:`~.EstimatorPubResult`.

    Args:
        result: An :class:`~.EstimatorPubResult`.
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

    Raises:
        ValueError: If ``result`` does not contain zero noise extrapolation data.
        ValueError: If the length of ``names`` is not equal to the length of ``indices``.
    """
    resilience = result.metadata.get("resilience")
    if not resilience:
        raise ValueError("Result does not contain resilience metadata.")

    zne_metadata = resilience.get("zne")
    if not zne_metadata:
        raise ValueError("Result does not contain ZNE data.")

    if indices is None:
        indices = [idx for idx in product(*(range(s) for s in result.data.shape))]

    if names is None:
        names = [f"evs_{o if len(o) != 1 else o[0]}" for o in indices]

    if len(indices) != len(names):
        raise ValueError(
            f"Length of names {len(names)} is not equal to the length of names {len(indices)}."
        )

    noise_factors = zne_metadata["noise_factors"]
    e_noise_factors = zne_metadata["extrapolated_noise_factors"]
    extrapolators = zne_metadata["extrapolators"]

    if subplots:
        colors = sample_colorscale(diverging.Spectral, np.linspace(0, 1, len(extrapolators)))
        div, mod = divmod(len(indices), n_cols)
        fig = make_subplots(
            cols=n_cols if div else mod,
            rows=div + bool(mod),
            shared_xaxes=True,
            subplot_titles=names,
        )
        models = set()
        for i, idx in enumerate(indices):
            div, mod = divmod(i, n_cols)
            evs = result.data.evs_noise_factors[idx]
            fig.add_trace(
                _marker_trace(
                    noise_factors,
                    evs,
                    result.data.stds_noise_factors[idx],
                    None,
                    i,
                    "black",
                    False,
                ),
                col=mod + 1,
                row=div + 1,
            )

            fig.update_yaxes(
                col=mod + 1, row=div + 1, range=[np.min(evs) - std_tol, np.max(evs) + std_tol]
            )

            for idx_m, model in enumerate(extrapolators):
                evs = result.data.evs_extrapolated[idx][idx_m]
                stds = result.data.stds_extrapolated[idx][idx_m]
                if any(stds > std_tol) or any(abs(evs) > mag_tol):
                    continue

                fig.add_traces(
                    _line_trace(
                        e_noise_factors,
                        evs,
                        stds,
                        n_stds,
                        model,
                        idx_m,
                        colors[idx_m],
                        model not in models,
                    ),
                    cols=mod + 1,
                    rows=div + 1,
                )
                models.add(model)

    else:
        colors = sample_colorscale(diverging.Spectral, np.linspace(0, 1, len(indices)))
        fig = make_subplots(cols=len(extrapolators), subplot_titles=extrapolators)
        for i, idx in enumerate(indices):
            show_legend = True
            color = colors[i]
            for idx_m in range(len(extrapolators)):
                evs = result.data.evs_extrapolated[idx][idx_m]
                stds = result.data.stds_extrapolated[idx][idx_m]
                if any(stds > std_tol) or any(abs(evs) > mag_tol):
                    continue

                fig.add_traces(
                    [
                        _marker_trace(
                            noise_factors,
                            result.data.evs_noise_factors[idx],
                            result.data.stds_noise_factors[idx],
                            names[i],
                            i,
                            color,
                            show_legend,
                        ),
                        *_line_trace(e_noise_factors, evs, stds, n_stds, None, i, color, False),
                    ],
                    rows=1,
                    cols=idx_m + 1,
                )
                show_legend = False

        fig.update_yaxes(
            range=[
                np.min(result.data.evs_noise_factors) - std_tol,
                np.max(result.data.evs_noise_factors) + std_tol,
            ],
        )

    fig.update_layout(
        height=height,
        width=width,
        plot_bgcolor="white",
    )

    fig.update_xaxes(
        mirror=True,
        ticks="outside",
        showline=True,
        linecolor="black",
        gridcolor="lightgrey",
    )

    fig.update_yaxes(
        mirror=True,
        ticks="outside",
        showline=True,
        linecolor="black",
        gridcolor="lightgrey",
    )

    return fig


def _line_trace(
    x_values,
    y_values,
    stds,
    n_stds: int = 1,
    name: str | None = None,
    legend_group: int | None = None,
    color: str | None = None,
    show_legend: bool = False,
) -> list[go.Scatter]:
    """Returns traces for a line plot with a standard deviation fill.
    
    Args:
        x_values:
        y_values:
        stds:
        n_stds:
        name:
        legend_group:
        color:
        show_legend:

    Returns:
        A list of traces.
    """
    return [
        go.Scatter(
            x=x_values,
            y=y_values,
            name=name,
            mode="lines",
            line=dict(color=color),
            legendgroup=legend_group,
            showlegend=show_legend,
        ),
        *(
            go.Scatter(
                x=x_values + x_values[::-1],
                y=(y_values + i * stds).tolist() + (y_values - i * stds).tolist()[::-1],
                fill="toself",
                fillcolor=color,
                line=dict(color="rgba(255,255,255,0)"),
                opacity=0.2,
                legendgroup=legend_group,
                hoverinfo="skip",
                showlegend=False,
            )
            for i in range(1, n_stds + 1)
        ),
    ]


def _marker_trace(x_values, y_values, stds, name, legend_group, color, show_legend) -> go.Scatter:
    """Return a trace for a scatter plot.
    
    Args:
        x_values:
        y_values:
        stds:
        name:
        legend_group:
        color:
        show_legend:

    Returns:
        A trace.
    """
    return go.Scatter(
        x=x_values,
        y=y_values,
        name=name,
        mode="markers",
        marker=dict(color=color),
        error_y=dict(array=stds),
        legendgroup=legend_group,
        showlegend=show_legend,
    )
