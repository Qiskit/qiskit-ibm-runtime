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

# pylint: disable=import-outside-toplevel

"""Functions to visualize :class:`~.NoiseLearnerResult` objects."""

from __future__ import annotations
from typing import Dict, Optional, Tuple, Union, TYPE_CHECKING

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
    color_out_of_scale: str = "lightgreen",
    num_edge_segments: int = 16,
    edge_width: float = 4,
    height: int = 500,
    highest_rate: Optional[float] = None,
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
        ModuleNotFoundError: If the required ``plotly`` dependencies cannot be imported.
    """
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
                get_rgb_color(
                    discreet_colorscale, v / highest_rate, color_no_data, color_out_of_scale
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
                discreet_colorscale, rate / highest_rate, color_no_data, color_out_of_scale
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


def draw_layer_error_1q_bar_plot(
    layer_error: LayerError,
    qubits: Optional[list[int]] = None,
    generators: Optional[list[str]] = None,
    colors: Optional[list[str]] = None,
    grouping: str = "qubit",
    height: int = 500,
    width: int = 800,
) -> go.Figure:
    r"""
    Draw a bar plot containing all the one-body terms in this :class:`~.LayerError`.

    Args:
        layer_error: The :class:`~.LayerError` to draw.
        qubits: The qubits to include in the bar plot. If ``None``, all the qubits in the given
            ``layer_error`` are included.
        generators: The (one-qubit) generators to include in the bar plot, e.g. ``("X", "Z")``. If
            ``None``, all the generators in the given ``layer_error`` are included.
        colors: A list of colors for the bars in the plot, or ``None`` if these colors are to be
            chosen automatically.
        grouping: How to group the bars. Available values are:
            * ``"qubits"``: Group by qubit.
            * ``"generator"``: Group the bar by generator.
        height: The height of the returned figure.
        width: The width of the returned figure.

    Raises:
        ValueError: If an invalid grouping option is given.
        ValueError: If ``colors`` is given but its length is incorrect.
        ModuleNotFoundError: If the required ``plotly`` dependencies cannot be imported.

    """
    try:
        import plotly.graph_objects as go
    except ModuleNotFoundError as msg:
        raise ModuleNotFoundError(f"Failed to import 'plotly' dependencies with error: {msg}.")

    fig = go.Figure(layout=go.Layout(width=width, height=height))
    fig.update_layout(
        xaxis_title="generators",
        yaxis_title="rates",
    )

    if grouping not in (allowed_groupings := ["qubit", "generator"]):
        raise ValueError(f"Grouping '{grouping}' not supported, use one of {allowed_groupings}.")

    num_qubits = len(qubits) if qubits else layer_error.num_qubits
    colors = colors if colors else [None] * num_qubits
    if len(colors) != num_qubits:
        raise ValueError(f"Expected {num_qubits} colors, found {len(colors)}.")

    one_body_err = layer_error.error.restrict_num_bodies(1)

    for i, qubit in enumerate(layer_error.qubits):
        if qubits and qubit not in qubits:
            continue

        mask = one_body_err.generators.x[:, i] | one_body_err.generators.z[:, i]
        qubit_generators = np.array(
            ["".join([p for p in g if p != "I"]) for g in one_body_err.generators[mask].to_labels()]
        )
        rates = one_body_err.rates[mask]

        if generators:
            mask_gen = [gen in generators for gen in qubit_generators]
            rates = rates[mask_gen]
            qubit_generators = qubit_generators[mask_gen]

        hoverinfo = [f"qubit: {qubit}"] * len(qubit_generators)
        for idx, (gen, rate) in enumerate(zip(qubit_generators, rates)):
            hoverinfo[idx] += f"<br>gen.: {gen}"
            hoverinfo[idx] += f"<br>rate: {rate}"

        if grouping == "qubit":
            qubit_generators = [gen + f"_{qubit}" for gen in qubit_generators]

        fig.add_trace(
            go.Bar(
                x=qubit_generators,
                y=rates,
                name=f"qubit: {qubit}",
                marker_color=colors[i],
                hovertemplate=hoverinfo,
            )
        )

    return fig


def draw_layer_error_2q_bar_plot(
    layer_error: LayerError,
    edges: Optional[list[tuple[int, int]]] = None,
    generators: Optional[list[str]] = None,
    colors: Optional[list[str]] = None,
    grouping: str = "edge",
    height: int = 500,
    width: int = 800,
) -> go.Figure:
    r"""
    Draw a bar plot containing all the two-body terms in this :class:`~.LayerError`.

    Args:
        layer_error: The :class:`~.LayerError` to draw.
        edges: The edges (specified as pairs of qubit labels) to include in the bar plot. If
            ``None``, all the edges in the given ``layer_error`` are included.
        generators: The (two-qubit) generators to include in the bar plot, e.g. ``("XY", "ZZ")``.
            If ``None``, all the generators in the given ``layer_error`` are included.
        colors: A list of colors for the bars in the plot, or ``None`` if these colors are to be
            chosen automatically.
        grouping: How to group the bars. Available values are:
            * ``"edge"``: Group by edge.
            * ``"generator"``: Group the bar by generator.
        height: The height of the returned figure.
        width: The width of the returned figure.

    Raises:
        ValueError: If an invalid grouping option is given.
        ValueError: If ``colors`` is given but its length is incorrect.
        ModuleNotFoundError: If the required ``plotly`` dependencies cannot be imported.

    """
    try:
        import plotly.graph_objects as go
    except ModuleNotFoundError as msg:
        raise ModuleNotFoundError(f"Failed to import 'plotly' dependencies with error: {msg}.")

    fig = go.Figure(layout=go.Layout(width=width, height=height))
    fig.update_layout(
        xaxis_title="generators",
        yaxis_title="rates",
    )

    if grouping not in (allowed_groupings := ["edge", "generator"]):
        raise ValueError(f"Grouping '{grouping}' not supported, use one of {allowed_groupings}.")

    qubits = layer_error.qubits
    two_body_err = layer_error.error.restrict_num_bodies(2)

    if edges:
        edges = [sorted(edge) for edge in edges]  # type: ignore
    else:
        edges = sorted(
            set(
                [qubits[idx] for idx, p in enumerate(g) if str(p) != "I"]  # type: ignore
                for g in two_body_err.generators
            )
        )

    colors = colors if colors else [None] * len(edges)
    if len(colors) != len(edges):
        raise ValueError(f"Expected {len(edges)} colors, found {len(colors)}.")

    for edge_idx, edge in enumerate(edges):
        if edge not in edges:
            continue

        mask = [
            (str(g[qubits.index(edge[0])]) != "I" and str(g[qubits.index(edge[1])]) != "I")
            for g in two_body_err.generators
        ]
        edge_generators = two_body_err.generators[mask].to_labels()
        edge_generators = np.array(["".join([p for p in g if p != "I"]) for g in edge_generators])
        rates = two_body_err.rates[mask]

        if generators:
            mask_gen = [gen in generators for gen in edge_generators]
            rates = rates[mask_gen]
            edge_generators = edge_generators[mask_gen]

        hoverinfo = [f"edge: {edge}"] * len(edge_generators)
        for idx, (gen, rate) in enumerate(zip(edge_generators, rates)):
            hoverinfo[idx] += f"<br>gen.: {gen}"
            hoverinfo[idx] += f"<br>rate: {rate}"

        if grouping == "edge":
            edge_generators = [gen + f"_{edge[0]},{edge[1]}" for gen in edge_generators]

        fig.add_trace(
            go.Bar(
                x=edge_generators,
                y=rates,
                name=f"edge: {edge}",
                marker_color=colors[edge_idx],
                hovertemplate=hoverinfo,
            )
        )

    return fig


def draw_layer_errors_swarm(
    layer_errors: list[LayerError],
    colors: Optional[list[str]] = None,
    bin_size: Optional[Union[int, float]] = None,
    opacities: Union[float, list[float]] = 0.4,
    names: Optional[list[str]] = None,
    height: int = 500,
    width: int = 800,
) -> go.Figure:
    r"""
    Draw a swarm plot for the given list of layer errors.

    This function plots the rates of each of the given layer errors along a vertical axes,
    offsetting the rates along the ``x`` axis so that they do not overlap with each other.

    Args:
        layer_errors: The layer errors to draw.
        colors: A list of colors for the markers in the plot, or ``None`` if these colors are to be
            chosen automatically.
        bin_size: The size of the bins that the rates are placed into prior to calculating the
            offsets. If ``None``, it automatically calculates the ``bin_size`` so that all the
            rates are placed in ``10`` consecutive bins.
        opacities: A list of opacities for the markers.
        names: The names of the various layers as displayed in the legend. If ``None``, default
            names are assigned based on the layers' position inside the ``layer_errors`` list.
        height: The height of the returned figure.
        width: The width of the returned figure.

    Raises:
        ValueError: If an invalid grouping option is given.
        ValueError: If ``colors`` is given but its length is incorrect.
        ModuleNotFoundError: If the required ``plotly`` dependencies cannot be imported.

    """
    try:
        import plotly.graph_objects as go
    except ModuleNotFoundError as msg:
        raise ModuleNotFoundError(f"Failed to import 'plotly' dependencies with error: {msg}.")

    fig = go.Figure(layout=go.Layout(width=width, height=height))
    fig.update_layout(
        xaxis_title="layers",
        yaxis_title="rates",
    )

    fig.update_xaxes(
        range=[-1, len(layer_errors)],
        showticklabels=False,
        showgrid=False,
        zeroline=False,
    )

    colors = colors if colors else [None] * len(layer_errors)
    if len(colors) != len(layer_errors):
        raise ValueError(f"Expected {len(layer_errors)} colors, found {len(colors)}.")

    opacities = [opacities] * len(layer_errors) if isinstance(opacities, float) else opacities
    if len(opacities) != len(layer_errors):
        raise ValueError(f"Expected {len(layer_errors)} opacities, found {len(opacities)}.")

    names = [f"layer #{i}" for i in range(len(layer_errors))] if not names else names
    if len(names) != len(layer_errors):
        raise ValueError(f"Expected {len(layer_errors)} names, found {len(names)}.")

    for layer_error_idx, layer_error in enumerate(layer_errors):
        min_rate = min(rates := layer_error.error.rates)
        max_rate = max(rates)

        bin_size = bin_size if bin_size else (max_rate - min_rate) / 10
        num_bins = int((max_rate - min_rate) // bin_size + 1)
        bins: dict[int, list[float]] = {i: [] for i in range(num_bins)}

        for rate in rates:
            bins[int((rate - min_rate) // bin_size)] += [rate]

        xs = []
        ys = []
        for b in bins.values():
            num_vals = len(b)
            xs += [layer_error_idx + (o - num_vals / 2) / len(rates) for o in range(num_vals)]
            ys += list(b)

        fig.add_trace(
            go.Scatter(
                y=ys,
                x=xs,
                mode="markers",
                marker={
                    "color": colors[layer_error_idx],
                    "opacity": opacities[layer_error_idx],
                },
                name=names[layer_error_idx],
            )
        )

    return fig
