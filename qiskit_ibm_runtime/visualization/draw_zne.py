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

"""Functions to visualize :class:`~.EstimatorPubResult` ZNE data."""

from __future__ import annotations

from itertools import product
from typing import Sequence, TYPE_CHECKING
import numpy as np

from .utils import plotly_module
from ..utils.estimator_pub_result import EstimatorPubResult

if TYPE_CHECKING:
    from plotly.graph_objects import Figure as PlotlyFigure
    from plotly.graph_objects import Scatter as PlotlyScatter


def draw_zne_evs(
    result: EstimatorPubResult,
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
    """Plot the zero noise extrapolation data in an :class:`~.EstimatorPubResult`.

    This function generates a subfigure for each estimated expectation value.

    Args:
        result: An :class:`~.EstimatorPubResult`.
        indices: The indices of the expectation values to include in the plot. If ``None``, includes all
            values. See :class:`~.ZneOptions` for information on the indexing scheme.
        names: The names to assign to the expectation values. If ``None``, the names correspond to the
            indices.
        num_stds: The number of standard deviations to include around each fit.
        max_mag: The maximum magnitude of expectation values to include. If ``evs_extrapolated`` has a
            greater magnitude than this value, the expectation value is omitted from the plot.
        max_std: The maximum standard deviation to include. If ``stds_extrapolated`` is greater than
            this value for an expectation value and extrapolator, the fit is omitted from the plot.
        height: The height of the plot in pixels.
        width: The width of the plot in pixels.
        num_cols: The maximum number of columns in the figure.
        colorscale: The colorscale to use.

    Returns:
        A plotly figure.

    Raises:
        ValueError: If ``result`` does not contain zero noise extrapolation data.
        ValueError: If the length of ``names`` is not equal to the length of ``indices``.
    """
    sample_colorscale = plotly_module(".colors").sample_colorscale
    make_subplots = plotly_module(".subplots").make_subplots
    zne_metadata = _validate_metadata(result.metadata)

    if indices is None:
        indices = [idx for idx in product(*(range(s) for s in result.data.shape)) if idx]

    if names is None:
        names = [f"evs_{o if len(o) != 1 else o[0]}" for o in indices]

    _validate_names(indices, names)

    noise_factors = zne_metadata["noise_factors"]
    e_noise_factors = zne_metadata["extrapolated_noise_factors"]
    extrapolators = zne_metadata["extrapolators"]

    colors = sample_colorscale(colorscale, np.linspace(0, 1, len(extrapolators)))
    div, mod = divmod(len(indices), num_cols)
    fig = make_subplots(
        cols=num_cols if div else mod, rows=div + bool(mod), shared_xaxes=True, subplot_titles=names
    )

    models = set()
    for i, idx in enumerate(indices):
        div, mod = divmod(i, num_cols)
        col = mod + 1
        row = div + 1
        evs = result.data.evs_noise_factors[idx]
        fig.add_trace(
            _scatter_trace(
                noise_factors,
                evs,
                result.data.stds_noise_factors[idx],
                name=names[i],
                color="black",
            ),
            col=col,
            row=row,
        )
        fig.update_yaxes(col=col, row=row, range=[np.min(evs) - max_std, np.max(evs) + max_std])
        for idx_m, model in enumerate(extrapolators):
            evs = result.data.evs_extrapolated[idx][idx_m]
            stds = result.data.stds_extrapolated[idx][idx_m]
            if any(stds > max_std) or any(abs(evs) > max_mag):
                continue
            fig.add_traces(
                _line_fill_trace(
                    e_noise_factors,
                    evs,
                    stds,
                    num_stds,
                    model,
                    idx_m,
                    colors[idx_m],
                    model not in models,
                ),
                cols=col,
                rows=row,
            )
            models.add(model)

    fig.update_layout(
        height=height,
        width=width,
        plot_bgcolor="white",
        hoverlabel_align="right",
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


def draw_zne_extrapolators(
    result: EstimatorPubResult,
    indices: Sequence[tuple[int, ...]] | None = None,
    names: Sequence[str] | None = None,
    num_stds: int = 1,
    max_mag: float = 10,
    max_std: float = 0.2,
    height: int = 500,
    width: int = 1000,
    colorscale: str = "Aggrnyl",
) -> PlotlyFigure:
    """Plot the zero noise extrapolation data in an :class:`~.EstimatorPubResult`.

    This function generates a subfigure for each extrapolator.

    Args:
        result: An :class:`~.EstimatorPubResult`.
        indices: The indices of the expectation values to include in the plot. If ``None``, includes all
            values. See :class:`~.ZneOptions` for information on the indexing scheme.
        names: The names to assign to the expectation values. If ``None``, the names correspond to the
            indices.
        num_stds: The number of standard deviations to include around each fit.
        max_mag: The maximum magnitude of expectation values to include. If ``evs_extrapolated`` has a
            greater magnitude than this value, the expectation value is omitted from the plot.
        max_std: The maximum standard deviation to include. If ``stds_extrapolated`` is greater than
            this value for an expectation value and extrapolator, the fit is omitted from the plot.
        height: The height of the plot in pixels.
        width: The width of the plot in pixels.
        colorscale: The colorscale to use.

    Returns:
        A plotly figure.

    Raises:
        ValueError: If ``result`` does not contain zero noise extrapolation data.
        ValueError: If the length of ``names`` is not equal to the length of ``indices``.
    """
    sample_colorscale = plotly_module(".colors").sample_colorscale
    make_subplots = plotly_module(".subplots").make_subplots
    zne_metadata = _validate_metadata(result.metadata)

    if indices is None:
        indices = [idx for idx in product(*(range(s) for s in result.data.shape)) if idx]

    if names is None:
        names = [f"evs_{o if len(o) != 1 else o[0]}" for o in indices]

    _validate_names(indices, names)

    noise_factors = zne_metadata["noise_factors"]
    e_noise_factors = zne_metadata["extrapolated_noise_factors"]
    extrapolators = zne_metadata["extrapolators"]

    colors = sample_colorscale(colorscale, np.linspace(0, 1, len(indices)))
    fig = make_subplots(cols=len(extrapolators), subplot_titles=extrapolators)
    for i, idx in enumerate(indices):
        show_legend = True
        color = colors[i]
        for idx_m, extrapolator in enumerate(extrapolators):
            evs = result.data.evs_extrapolated[idx][idx_m]
            stds = result.data.stds_extrapolated[idx][idx_m]
            if any(stds > max_std) or any(abs(evs) > max_mag):
                continue
            fig.add_traces(
                [
                    _scatter_trace(
                        noise_factors,
                        result.data.evs_noise_factors[idx],
                        result.data.stds_noise_factors[idx],
                        names[i],
                        i,
                        color,
                        show_legend,
                    ),
                    *_line_fill_trace(
                        e_noise_factors,
                        evs,
                        stds,
                        num_stds,
                        name=extrapolator,
                        legend_group=i,
                        color=color,
                    ),
                ],
                rows=1,
                cols=idx_m + 1,
            )
            show_legend = False

    fig.update_layout(
        height=height,
        width=width,
        plot_bgcolor="white",
        hoverlabel_align="right",
    )

    fig.update_xaxes(
        mirror=True,
        ticks="outside",
        showline=True,
        linecolor="black",
        gridcolor="lightgrey",
    )

    fig.update_yaxes(
        range=[
            np.min(result.data.evs_noise_factors) - max_std,
            np.max(result.data.evs_noise_factors) + max_std,
        ],
        mirror=True,
        ticks="outside",
        showline=True,
        linecolor="black",
        gridcolor="lightgrey",
    )

    return fig


def _line_fill_trace(
    x_values: np.array,
    y_values: np.array,
    stds: np.array,
    num_stds: int = 1,
    name: str | None = None,
    legend_group: int | None = None,
    color: str | None = None,
    show_legend: bool = False,
) -> list[PlotlyScatter]:
    """Return a list of traces for a line plot with a standard deviation fill.

    Args:
        x_values: The values for the x-axis.
        y_values: The values for the y-axis.
        stds: The standard deviation for the ``y_values``.
        num_stds: The number of standard deviations to include around the line plot.
        name: The name of this trace.
        legend_group: The legend group that this trace belongs to.
        color: The color of the fill around the line.
        show_legend: Whether to show this trace on a figure.

    Returns:
        A list of traces.
    """
    go = plotly_module(".graph_objects")
    hovertemplate = "extrapolator: " + name + "<br>noise_factor: %{x}<br>ev_extrap: %{y:.4f}"
    hovertemplate += "<br>std: %{customdata:.4f}<extra></extra>"
    return [
        go.Scatter(
            x=x_values,
            y=y_values,
            customdata=stds,
            name=name,
            mode="lines",
            line={"color": color},
            hovertemplate=hovertemplate,
            legendgroup=legend_group,
            showlegend=show_legend,
        ),
        *(
            go.Scatter(
                x=x_values + x_values[::-1],
                y=(y_values + i * stds).tolist() + (y_values - i * stds).tolist()[::-1],
                fill="toself",
                fillcolor=color,
                line={"color": "rgba(255,255,255,0)"},
                opacity=0.2,
                legendgroup=legend_group,
                hoverinfo="skip",
                showlegend=False,
            )
            for i in range(1, num_stds + 1)
        ),
    ]


def _scatter_trace(
    x_values: np.array,
    y_values: np.array,
    stds: np.array,
    name: str | None = None,
    legend_group: int | None = None,
    color: str | None = None,
    show_legend: bool = False,
) -> PlotlyScatter:
    """Return a trace for a scatter plot with error bars.

    Args:
        x_values: The values for the x-axis.
        y_values: The values for the y-axis.
        stds: The standard deviation for the ``y_values``.
        name: The name of this trace.
        legend_group: The legend group that this trace belongs to.
        color: The color of the markers.
        show_legend: Whether to show this trace on a legend.

    Returns:
        A trace containing a scatter plot.
    """
    go = plotly_module(".graph_objects")
    return go.Scatter(
        x=x_values,
        y=y_values,
        error_y={"array": stds},
        name=name,
        mode="markers",
        marker={"color": color},
        hovertemplate="noise_factor: %{x} <br>ev: %{y:.4f}<br>std: %{error_y.array:.4f}<extra></extra>",
        legendgroup=legend_group,
        showlegend=show_legend,
    )


def _validate_names(indices: Sequence[tuple[int, ...]], names: Sequence[str]) -> None:
    """Validate that the indices and names provided are compatible.

    Raises:
        ValueError: If the indices and names are different lengths.
    """
    if len(indices) != len(names):
        raise ValueError(
            f"Length of names {len(names)} is not equal to the length of indices {len(indices)}."
        )


def _validate_metadata(metadata: dict) -> dict:
    """Validate that the metadata contains ZNE metadata and return it.

    Raises:
        ValueError: If metadata does not contain ZNE metadata.

    Returns:
        The ZNE metadata.
    """
    if not (resilience := metadata.get("resilience")):
        raise ValueError(
            "Result does not contain resilience metadata. Enable ZNE options on an estimator to use "
            "this function."
        )

    if not (zne_metadata := resilience.get("zne")):
        raise ValueError(
            "Result does not contain ZNE data. Enable ZNE options on an estimator to use this function."
        )

    return zne_metadata
