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

"""Functions to visualize :class:`~.NoiseLearnerResult` objects."""

from __future__ import annotations
from typing import Any, Dict, Optional, Tuple, Union, TYPE_CHECKING

import numpy as np
from qiskit.providers.backend import BackendV2
from qiskit.quantum_info import Pauli

from ..utils.embeddings import Embedding
from ..utils.noise_learner_result import LayerError
from .utils import get_rgb_color, pie_slice, plotly_module

if TYPE_CHECKING:
    from plotly.graph_objects import Figure as PlotlyFigure


def draw_layer_error_map(
    layer_error: LayerError,
    embedding: Union[Embedding, BackendV2],
    colorscale: str = "Bluered",
    color_no_data: str = "lightgray",
    color_out_of_scale: str = "lightgreen",
    num_edge_segments: int = 16,
    edge_width: float = 4,
    height: int = 500,
    highest_rate: Optional[float] = None,
    background_color: str = "white",
    radius: float = 0.25,
    width: int = 800,
) -> PlotlyFigure:
    r"""
    Draw a map view of a :class:`~.LayerError`.

    Args:
        layer_error: The :class:`~.LayerError` to draw.
        embedding: An :class:`~.Embedding` object containing the coordinates and coupling map
            to draw the layer error on, or a backend to generate an :class:`~.Embedding` for.
        colorscale: The colorscale used to show the rates of ``layer_error``.
        color_no_data: The color used for qubits and edges for which no data is available.
        color_out_of_scale: The color used for rates with value greater than ``highest_rate``.
        num_edge_segments: The number of equal-sized segments that edges are made of.
        edge_width: The line width of the edges in pixels.
        height: The height of the returned figure.
        highest_rate: The highest rate, used to normalize all other rates before choosing their
            colors. If ``None``, it defaults to the highest value found in the ``layer_error``.
        background_color: The background color.
        radius: The radius of the pie charts representing the qubits.
        width: The width of the returned figure.

    Raises:
        ValueError: If the given coordinates are incompatible with the specified backend.
        ValueError: If ``backend`` has no coupling map.
    """
    go = plotly_module(".graph_objects")
    sample_colorscale = plotly_module(".colors").sample_colorscale

    fig = go.Figure(layout=go.Layout(width=width, height=height))

    if isinstance(embedding, BackendV2):
        embedding = Embedding.from_backend(embedding)
    coordinates = embedding.coordinates
    coupling_map = embedding.coupling_map

    # The coordinates come in the format ``(row, column)`` and place qubit ``0`` in the bottom row.
    # We turn them into ``(x, y)`` coordinates for convenience, multiplying the ``ys`` by ``-1`` so
    # that the map matches the map displayed on the ibmq website.
    ys = [-row for row, _ in coordinates]
    xs = [col for _, col in coordinates]

    # A set of unique edges ``(i, j)``, with ``i < j``.
    edges = set(tuple(sorted(edge)) for edge in list(coupling_map))

    # The highest rate
    max_rate = 0

    # Initialize a dictionary of one-qubit errors
    qubits = layer_error.qubits
    error_1q = layer_error.error.restrict_num_bodies(1)
    rates_1q: Dict[int, Dict[str, float]] = {qubit: {} for qubit in qubits}
    for pauli, rate in zip(error_1q.generators, error_1q.rates):
        qubit_idx = np.where(pauli.x | pauli.z)[0][0]
        rates_1q[qubits[qubit_idx]][str(pauli[qubit_idx])] = rate
        max_rate = max(max_rate, rate)

    # Initialize a dictionary of two-qubit errors
    error_2q = layer_error.error.restrict_num_bodies(2)
    rates_2q: Dict[Tuple[int, ...], Dict[str, float]] = {edge: {} for edge in edges}
    for pauli, rate in zip(error_2q.generators, error_2q.rates):
        err_idxs = tuple(sorted([i for i, q in enumerate(pauli) if str(q) != "I"]))
        edge = (qubits[err_idxs[0]], qubits[err_idxs[1]])
        rates_2q[edge][str(pauli[[err_idxs[0], err_idxs[1]]])] = rate
        max_rate = max(max_rate, rate)

    highest_rate = highest_rate if highest_rate else max_rate

    # A discrete colorscale that contains 1000 hues.
    discrete_colorscale = sample_colorscale(colorscale, np.linspace(0, 1, 1000))

    # Plot the edges
    for q1, q2 in edges:
        x0 = xs[q1]
        x1 = xs[q2]
        y0 = ys[q1]
        y1 = ys[q2]

        if vals := rates_2q[(q1, q2)].values():
            # Add gradient. Gradients are currently not supported for go.Scatter lines, so we break
            # the line into segments and draw `num_edge_segments` segments of increasing colors.
            min_val = min(vals)
            max_val = min(max(vals), 1)
            all_vals = [
                min_val + (max_val - min_val) / num_edge_segments * i
                for i in range(num_edge_segments)
            ]
            color = [
                get_rgb_color(
                    discrete_colorscale, v / highest_rate, color_no_data, color_out_of_scale
                )
                for v in all_vals
            ]
            hoverinfo_2q = ""
            for pauli, rate in rates_2q[(q1, q2)].items():
                hoverinfo_2q += f"<br>{pauli}: {rate}"

            for i in range(num_edge_segments):
                # Add a trace for the edge
                edge = go.Scatter(
                    x=[
                        x0 + (x1 - x0) / num_edge_segments * i,
                        x0 + (x1 - x0) / num_edge_segments * (i + 1),
                    ],
                    y=[
                        y0 + (y1 - y0) / num_edge_segments * i,
                        y0 + (y1 - y0) / num_edge_segments * (i + 1),
                    ],
                    hovertemplate=hoverinfo_2q,
                    mode="lines",
                    line={
                        "color": color[i],
                        "width": edge_width,
                    },
                    showlegend=False,
                    name="",
                )
                fig.add_trace(edge)
        else:
            # Add a line for the edge
            edge = go.Scatter(
                x=[x0, x1],
                y=[y0, y1],
                hovertemplate="No data",
                mode="lines",
                line={
                    "color": color_no_data,
                    "width": edge_width,
                },
                showlegend=False,
                name="",
            )
            fig.add_trace(edge)

    # Plot the pie charts showing X, Y, and Z for each qubit
    shapes = []
    hoverinfo_1q = []  # the info displayed when hovering over the pie charts
    for qubit, (x, y) in enumerate(zip(xs, ys)):
        hoverinfo = ""
        for pauli, angle in [("Z", -30), ("X", 90), ("Y", 210)]:
            rate = rates_1q.get(qubit, {}).get(pauli, 0)
            fillcolor = get_rgb_color(
                discrete_colorscale, rate / highest_rate, color_no_data, color_out_of_scale
            )
            shapes += [
                {
                    "type": "path",
                    "path": pie_slice(angle, angle + 120, x, y, radius),
                    "fillcolor": fillcolor,
                    "line_color": "black",
                    "line_width": 1,
                },
            ]

            if rate:
                hoverinfo += f"<br>{pauli}: {rate}"
        hoverinfo_1q += [hoverinfo or "No data"]

        # Add annotation with qubit label
        fig.add_annotation(x=x + 0.3, y=y + 0.4, text=f"{qubit}", showarrow=False)

    # Add the hoverinfo for the pie charts
    marker_colors = []
    for qubit in rates_1q:
        max_qubit_rate = max(rates_1q[qubit].values())
        marker_colors.append(max_qubit_rate if max_qubit_rate <= highest_rate else highest_rate)
    nodes = go.Scatter(
        x=xs,
        y=ys,
        mode="markers",
        marker={
            "color": marker_colors,
            "colorscale": colorscale,
            "showscale": True,
        },
        hovertemplate=hoverinfo_1q,
        showlegend=False,
        name="",
    )
    fig.add_trace(nodes)

    # Add a "legend" pie to show how pies work
    x_legend = max(xs) + 1
    y_legend = max(ys)
    for pauli, angle, slice_color in [
        ("Z", -30, "lightgreen"),
        ("X", 90, "dodgerblue"),
        ("Y", 210, "khaki"),
    ]:
        shapes += [
            {
                "type": "path",
                "path": pie_slice(angle, angle + 120, x_legend, y_legend, 0.5),
                "fillcolor": slice_color,
                "line_color": "black",
                "line_width": 1,
            },
        ]
    fig.update_layout(shapes=shapes)

    # Add the annotations on top of the legend pie
    fig.add_annotation(x=x_legend + 0.2, y=y_legend, text="<b>Z</b>", showarrow=False, yshift=10)
    fig.add_annotation(x=x_legend - 0.2, y=y_legend, text="<b>X</b>", showarrow=False, yshift=10)
    fig.add_annotation(x=x_legend, y=y_legend - 0.45, text="<b>Y</b>", showarrow=False, yshift=10)

    # Set x and y range
    fig.update_xaxes(
        range=[min(xs) - 1, max(xs) + 2],
        showticklabels=False,
        showgrid=False,
        zeroline=False,
    )
    fig.update_yaxes(
        range=[min(ys) - 1, max(ys) + 1],
        showticklabels=False,
        showgrid=False,
        zeroline=False,
    )

    # Ensure that the circle is non-deformed
    fig.update_yaxes(scaleanchor="x", scaleratio=1)
    fig.update_layout(plot_bgcolor=background_color)

    return fig


def draw_layer_errors_swarm(
    layer_errors: list[LayerError],
    num_bodies: Optional[int] = None,
    max_rate: Optional[float] = None,
    min_rate: Optional[float] = None,
    connected: Optional[list[Union[Pauli, str]]] = None,
    colors: Optional[list[str]] = None,
    num_bins: Optional[int] = None,
    opacities: Union[float, list[float]] = 0.4,
    names: Optional[list[str]] = None,
    x_coo: Optional[list[float]] = None,
    marker_size: Optional[float] = None,
    height: int = 500,
    width: int = 800,
) -> PlotlyFigure:
    r"""
    Draw a swarm plot for the given list of layer errors.

    This function plots the rates of each of the given layer errors along a vertical axes,
    offsetting the rates along the ``x`` axis to minimize the overlap between the markers. It helps
    visualizing the distribution of errors for different layer errors, as well as to track (using
    the ``connected`` argument) the evolution of specific generators across different layers.

    .. note::

        To calculate the offsets, this arranges the rates in ``num_bins`` equally-spaced bins, and
        then it assigns the ``x`` coordinates so that all the rates in the same bins are spaced
        around the vertical axis. Thus, a higher value of ``num_bins`` will result in higher
        overlaps between the markers.

    Args:
        layer_errors: The layer errors to draw.
        num_bodies: The weight of the generators to include in the plot, or ``None`` if all the
            generators should be included.
        max_rate: The largest rate to include in the plot, or ``None`` if no upper limit should be
            set.
        min_rate: The smallest rate to include in the plot, or ``None`` if no lower limit should be
            set.
        connected: A list of generators whose markers are to be connected by lines.
        colors: A list of colors for the markers in the plot, or ``None`` if these colors are to be
            chosen automatically.
        num_bins: The number of bins to place the rates into when calculating the ``x``-axis
            offsets.
        opacities: A list of opacities for the markers.
        names: The names of the various layers as displayed in the legend. If ``None``, default
            names are assigned based on the layers' position inside the ``layer_errors`` list.
        x_coo: The ``x``-axis coordinates of the vertical axes that the markers are drawn around, or
            ``None`` if these axes should be placed at regular intervals.
        marker_size: The size of the marker in the plot.
        height: The height of the returned figure.
        width: The width of the returned figure.

    Raises:
        ValueError: If an invalid grouping option is given.
        ValueError: If ``colors`` is given but its length is incorrect.
    """
    go = plotly_module(".graph_objects")

    colors = colors if colors else ["dodgerblue"] * len(layer_errors)
    if len(colors) != len(layer_errors):
        raise ValueError(f"Expected {len(layer_errors)} colors, found {len(colors)}.")

    opacities = [opacities] * len(layer_errors) if isinstance(opacities, float) else opacities
    if len(opacities) != len(layer_errors):
        raise ValueError(f"Expected {len(layer_errors)} opacities, found {len(opacities)}.")

    names = [f"layer #{i}" for i in range(len(layer_errors))] if not names else names
    if len(names) != len(layer_errors):
        raise ValueError(f"Expected {len(layer_errors)} names, found {len(names)}.")

    x_coo = list(range(len(layer_errors))) if not x_coo else x_coo
    if len(x_coo) != len(layer_errors):
        raise ValueError(f"Expected {len(layer_errors)} ``x_coo``, found {len(x_coo)}.")

    fig = go.Figure(layout=go.Layout(width=width, height=height))
    fig.update_xaxes(
        range=[x_coo[0] - 1, x_coo[-1] + 1],
        showgrid=False,
        zeroline=False,
        title="layers",
    )
    fig.update_yaxes(title="rates")
    fig.update_layout(xaxis={"tickvals": x_coo, "ticktext": names})

    # Initialize a dictionary to store the coordinates of the generators that need to be connected
    connected_d: dict[str, dict[str, list[float]]] = (
        {str(p): {"xs": [], "ys": []} for p in connected} if connected else {}
    )

    for l_error_idx, l_error in enumerate(layer_errors):
        error = l_error.error.restrict_num_bodies(num_bodies) if num_bodies else l_error.error
        generators = error.generators.to_labels()
        smallest_rate = min(rates := error.rates)
        highest_rate = max(rates)

        # Create bins
        num_bins = num_bins or 10
        bin_size = (highest_rate - smallest_rate) / num_bins
        bins: dict[int, list[Any]] = {i: [] for i in range(num_bins + 1)}

        # Populate the bins
        for idx, (gen, rate) in enumerate(zip(generators, rates)):
            if gen not in connected_d:
                if (min_rate and rate < min_rate) or (max_rate and rate > max_rate):
                    continue
            bins[int((rate - smallest_rate) // bin_size)] += [(gen, rate, gen in connected_d)]

        # Assign `x` and `y` coordinates based on the bins
        xs = []
        ys = []
        hoverinfo = []
        for values in bins.values():
            for idx, (gen, rate, is_connected) in enumerate(values):
                xs.append(x := x_coo[l_error_idx] + (idx - len(values) // 2) / len(rates))
                ys.append(rate)
                hoverinfo.append(f"Generator: {gen}<br>  rate: {rate}")

                if is_connected:
                    connected_d[gen]["xs"].append(x)
                    connected_d[gen]["ys"].append(rate)

        # Add the traces for the swarm plot of this layer error
        fig.add_trace(
            go.Scatter(
                y=ys,
                x=xs,
                hovertemplate=hoverinfo,
                mode="markers",
                marker={
                    "color": colors[l_error_idx],
                    "opacity": opacities[l_error_idx],
                    "size": marker_size,
                },
                name=names[l_error_idx],
                showlegend=False,
            )
        )

    # Add the traces for the tracked errors
    for gen, vals in connected_d.items():
        hoverinfo = [
            f"{name}<br>  gen.: {gen}<br>  rate: {y}" for name, y in zip(names, vals["ys"])
        ]

        fig.add_trace(
            go.Scatter(
                y=vals["ys"],
                x=vals["xs"],
                mode="lines+markers",
                name=str(gen),
                hovertemplate=hoverinfo,
            )
        )

    return fig
