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
from typing import List, Optional, Tuple

import numpy as np
import plotly.graph_objects as go
from plotly.express.colors import sample_colorscale
from qiskit.providers.backend import BackendV2

from ..utils.noise_learner_result import LayerError
from .utils import get_qubits_coordinates


def _pie_slice(angle_st, angle_end, x, y, radius):
    r"""
    Returns the path used to draw a slice of a pie chart.

    Note: To draw pie charts we use paths and shapes, as they are easier to place in a specific
    location than `go.Pie` objects.

    Args:
        angle_st: The angle where the slice begins.
        angle_end: The angle where the slice ends.
        x: The `x` coordinate of the centre of the pie.
        y: The `y` coordinate of the centre of the pie.
        radius: the radius of the pie.
    """
    t = np.linspace(angle_st * np.pi / 180, angle_end * np.pi / 180, 10)

    path_xs = x + radius * np.cos(t)
    path_ys = y + radius * np.sin(t)
    path = f"M {path_xs[0]},{path_ys[0]}"

    for xc, yc in zip(path_xs[1:], path_ys[1:]):
        path += f" L{xc},{yc}"
    path += f"L{x},{y} Z"

    return path


def _get_rgb_color(discreet_colorscale, rate, default):
    r"""
    Maps a continuous rate to an RGB color based on a discreet colorscale that contains
    exactly ``1000`` hues.

    Args:
        discreet_colorscale: A discreet colorscale.
        rate: A rate.
        default: A default color returned when ``rate`` is ``0``.
    """
    if len(discreet_colorscale) != 1000:
        raise ValueError("Invalid ``discreet_colorscale.``")

    if rate >= 1:
        return discreet_colorscale[-1]
    if rate == 0:
        return default
    return discreet_colorscale[int(np.round(rate, 3) * 1000)]


def draw_layer_error_map(
    layer_error: LayerError,
    backend: BackendV2,
    coordinates: Optional[List[Tuple[int, int]]] = None,
    *,
    colorscale: str = "Bluered",
    color_no_data: str = "lightgray",
    height: int = 500,
    plot_bgcolor: str = "white",
    radius: float = 0.25,
    width: int = 800,
) -> go.Figure:
    r"""
    Draws a map view of a :class:`~.LayerError`.

    Args:
        layer_error: The :class:`~.LayerError` to draw.
        backend: The backend on top of which the layer error is drawn.
        coordinates: A list of coordinates in the form ``(row, column)`` that allow drawing each
            qubit in the given backend on a 2D grid.
        colorscale: The colorscale used to show the rates of ``layer_error``.
        color_no_data: The color used for qubits and edges for which no data is available.
        height: The height of the returned figure.
        plot_bgcolor: The background color.
        radius: The radius of the pie charts representing the qubits.
        width: The width of the returned figure.

    """
    fig = go.Figure(layout=go.Layout(width=width, height=height))

    if not coordinates:
        coordinates = get_qubits_coordinates(backend.num_qubits)
    if len(coordinates) != backend.num_qubits:
        raise ValueError("Given coordinates are incompatible with the specified backend.")
    # The coordinates come in the format ``(row, column)`` and place qubit ``0`` in the bottom row.
    # We turn them into ``(x, y)`` coordinates for convenience, multiplying the ``ys`` by ``-1`` so
    # that the map matches the map displayed on the ibmq website.
    ys = [-row for row, _ in coordinates]
    xs = [col for _, col in coordinates]

    if backend.coupling_map is None:
        raise ValueError("Given backend has no coupling map.")
    # A set of unique edges ``(i, j)``, with ``i < j``.
    edges = set(tuple(sorted(edge)) for edge in list(backend.coupling_map))

    # The highest rate, used to normalize all other rates before choosing their colors.
    high_scale = 0

    # Initialize a dictionary of one-qubit errors
    error_1q = layer_error.error.n_body(1)
    rates_1q = {qubit: {} for qubit in layer_error.qubits}
    for pauli, rate in zip(error_1q.generators, error_1q.rates):
        qubit = np.where(pauli.x | pauli.z)[0][0]
        rates_1q[qubit][str(pauli[qubit])] = rate
        high_scale = max(high_scale, rate)

    # Initialize a dictionary of two-qubit errors
    error_2q = layer_error.error.n_body(2)
    rates_2q = {qubits: {} for qubits in edges}
    for pauli, rate in zip(error_2q.generators, error_2q.rates):
        qubits = tuple(sorted([i for i, q in enumerate(pauli) if str(q) != "I"]))
        rates_2q[qubits][str(pauli[[qubits[0], qubits[1]]])] = rate
        high_scale = max(high_scale, rate)

    # A discreet colorscale that contains 1000 hues.
    discreet_colorscale = sample_colorscale(colorscale, np.linspace(0, 1, 1000))

    # Plot the edges
    for q1, q2 in edges:
        x0 = xs[q1]
        x1 = xs[q2]
        y0 = ys[q1]
        y1 = ys[q2]
        dx = 0 if x0 == x1 else 1.2 * radius
        dy = 0 if y0 == y1 else -1.2 * radius

        if vals := rates_2q[(q1, q2)].values():
            # Add gradient (currently not supported for go.Scatter)
            min_val = min(vals)
            max_val = min(max(vals), 1)
            all_vals = [min_val + (max_val - min_val) / 16 * i for i in range(16)]
            color = [
                _get_rgb_color(discreet_colorscale, v / high_scale, color_no_data) for v in all_vals
            ]
            hoverinfo_2q = ""
            for pauli, rate in rates_2q[(q1, q2)].items():
                hoverinfo_2q += f"<br>{pauli}: {rate}"
        else:
            color = color_no_data
            hoverinfo_2q = "No data"

        # Add a trace for the edge
        edge = go.Scatter(
            x=[x0 + dx + (x1 - 2 * dx - x0) / 16 * i for i in range(16)],
            y=[y0 + dy + (y1 - 2 * dy - y0) / 16 * i for i in range(16)],
            hovertemplate=hoverinfo_2q,
            mode="markers",
            marker={"color": color},
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
            fillcolor = _get_rgb_color(discreet_colorscale, rate / high_scale, color_no_data)
            shapes += [
                {
                    "type": "path",
                    "path": _pie_slice(angle, angle + 120, x, y, radius),
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
    nodes = go.Scatter(
        x=xs,
        y=ys,
        mode="markers",
        marker={
            "color": list({qubit: max(rates_1q[qubit].values()) for qubit in rates_1q}.values()),
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
    for pauli, angle, color in [
        ("Z", -30, "lightgreen"),
        ("X", 90, "dodgerblue"),
        ("Y", 210, "khaki"),
    ]:
        shapes += [
            {
                "type": "path",
                "path": _pie_slice(angle, angle + 120, x_legend, y_legend, 0.5),
                "fillcolor": color,
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
    fig.update_layout(plot_bgcolor=plot_bgcolor)

    return fig
