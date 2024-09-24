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
from typing import Dict, Tuple, Union, TYPE_CHECKING

import numpy as np
from qiskit.providers.backend import BackendV2

from ..utils.embeddings import Embedding
from ..utils.noise_learner_result import LayerError
from .utils import get_rgb_color, pie_slice

if TYPE_CHECKING:
    import plotly.graph_objs as go


def draw_layer_error_map(
    layer_error: LayerError,
    embedding: Union[Embedding, BackendV2],
    colorscale: str = "Bluered",
    color_no_data: str = "lightgray",
    num_edge_segments: int = 16,
    edge_width: float = 4,
    height: int = 500,
    background_color: str = "white",
    radius: float = 0.25,
    width: int = 800,
) -> go.Figure:
    r"""
    Draw a map view of a :class:`~.LayerError`.

    Args:
        layer_error: The :class:`~.LayerError` to draw.
        embedding: An :class:`~.Embedding` object containing the coordinates and coupling map
            to draw the layer error on, or a backend to generate an :class:`~.Embedding` for.
        colorscale: The colorscale used to show the rates of ``layer_error``.
        color_no_data: The color used for qubits and edges for which no data is available.
        num_edge_segments: The number of equal-sized segments that edges are made of.
        edge_width: The line width of the edges in pixels.
        height: The height of the returned figure.
        background_color: The background color.
        radius: The radius of the pie charts representing the qubits.
        width: The width of the returned figure.

    Raises:
        ValueError: If the given coordinates are incompatible with the specified backend.
        ValueError: If ``backend`` has no coupling map.
        ModuleNotFoundError: If the required ``plotly`` dependencies cannot be imported.
    """
    # pylint: disable=import-outside-toplevel

    try:
        import plotly.graph_objects as go
        from plotly.colors import sample_colorscale
    except ModuleNotFoundError as msg:
        raise ModuleNotFoundError(f"Failed to import 'plotly' dependencies with error: {msg}.")

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

    # The highest rate, used to normalize all other rates before choosing their colors.
    high_scale = 0

    # Initialize a dictionary of one-qubit errors
    error_1q = layer_error.error.restrict_num_bodies(1)
    rates_1q: Dict[int, Dict[str, float]] = {qubit: {} for qubit in layer_error.qubits}
    for pauli, rate in zip(error_1q.generators, error_1q.rates):
        qubit = np.where(pauli.x | pauli.z)[0][0]
        rates_1q[qubit][str(pauli[qubit])] = rate
        high_scale = max(high_scale, rate)

    # Initialize a dictionary of two-qubit errors
    error_2q = layer_error.error.restrict_num_bodies(2)
    rates_2q: Dict[Tuple[int, ...], Dict[str, float]] = {qubits: {} for qubits in edges}
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
                get_rgb_color(discreet_colorscale, v / high_scale, color_no_data) for v in all_vals
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
            fillcolor = get_rgb_color(discreet_colorscale, rate / high_scale, color_no_data)
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
