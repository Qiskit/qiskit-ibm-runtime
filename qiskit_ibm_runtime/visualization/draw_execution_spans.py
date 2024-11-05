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

"""Functions to visualize :class:`~.ExecutionSpans` objects."""

from __future__ import annotations

from itertools import cycle
from datetime import datetime, timedelta
from typing import Iterable, TYPE_CHECKING

from ..execution_span import ExecutionSpan, ExecutionSpans
from .utils import plotly_module

if TYPE_CHECKING:
    from plotly.graph_objects import Figure as PlotlyFigure


HOVER_TEMPLATE = "<br>".join(
    [
        "<b>{name}[{idx}]</b>",
        "<b>&nbsp;&nbsp;&nbsp;Start:</b> {span.start:%Y-%m-%d %H:%M:%S.%f}",
        "<b>&nbsp;&nbsp;&nbsp;Stop:</b> {span.stop:%Y-%m-%d %H:%M:%S.%f}",
        "<b>&nbsp;&nbsp;&nbsp;Duration:</b> {span.duration:.4g}s",
        "<b>&nbsp;&nbsp;&nbsp;Size:</b> {span.size}",
        "<b>&nbsp;&nbsp;&nbsp;Pub Indexes:</b> {idxs}",
    ]
)


def _get_idxs(span: ExecutionSpan, limit: int = 10) -> str:
    if len(idxs := span.pub_idxs) <= limit:
        return str(idxs)
    else:
        return f"[{', '.join(map(str, idxs[:limit]))}, ...]"


def _get_id(spans: ExecutionSpans, multiple: bool) -> str:
    return f"<{hex(id(spans))}>" if multiple else ""


def draw_execution_spans(
    *spans: ExecutionSpans,
    names: str | Iterable[str] | None = None,
    common_start: bool = False,
    normalize_y: bool = False,
    line_width: int = 4,
    show_legend: bool = None,
) -> PlotlyFigure:
    """Draw one or more :class:`~.ExecutionSpans` on a bar plot.

    Args:
        spans: One or more :class:`~.ExecutionSpans`.
        names: Name or names to assign to respective ``spans``.
        common_start: Whether to shift all collections of spans so that their first span's start is
            at :math:`t=0`.
        normalize_y: Whether to display the y-axis units as a percentage of work complete, rather
            than cumulative shots completed.
        line_width: The thickness of line segments.
        show_legend: Whether to show a legend. By default, this choice is automatic.

    Returns:
        A plotly figure.
    """
    go = plotly_module(".graph_objects")
    colors = plotly_module(".colors").qualitative.Plotly

    fig = go.Figure()

    # assign a name to each span
    all_names = []
    if names is None:
        show_legend = False if show_legend is None else show_legend
    else:
        show_legend = True if show_legend is None else show_legend
        if isinstance(names, str):
            all_names = [names]
        else:
            all_names.extend(names)

    # make sure there are always at least as many names as span sets
    all_names.extend(
        f"ExecutionSpans{_get_id(single_span, len(spans)>1)}"
        for single_span in spans[len(all_names) :]
    )

    # loop through and make a trace in the figure for each ExecutionSpans
    for single_spans, color, name in zip(spans, cycle(colors), all_names):
        if not single_spans:
            continue

        # sort the spans but remember their original order
        sorted_spans = sorted(enumerate(single_spans), key=lambda x: x[1])

        offset = timedelta()
        if common_start:
            # plotly doesn't have a way to display timedeltas or relative times on a axis. the
            # standard workaround i've found is to shift times to t=0 (ie unix epoch) and suppress
            # showing the year/month in the tick labels.
            first_start = sorted_spans[0][1].start.replace(tzinfo=None)
            offset = first_start - datetime(year=1970, month=1, day=1)

        # gather x/y/text data for each span
        total_size = sum(span.size for span in single_spans) if normalize_y else 1
        y_value = 0.0
        x_data = []
        y_data = []
        text_data = []
        for idx, span in sorted_spans:
            y_value += span.size / total_size
            text = HOVER_TEMPLATE.format(span=span, idx=idx, idxs=_get_idxs(span), name=name)

            x_data.extend([span.start - offset, span.stop - offset, None])
            y_data.extend([y_value, y_value, None])
            text_data.extend([text] * 3)

        # add the data to the plot
        fig.add_trace(
            go.Scatter(
                x=x_data,
                y=y_data,
                mode="lines",
                line={"width": line_width, "color": color},
                text=text_data,
                hoverinfo="text",
                name=name,
            )
        )

    # axis and layout settings
    fig.update_layout(
        xaxis={"title": "Time", "type": "date"},
        showlegend=show_legend,
        legend={"yanchor": "bottom", "y": 0.01, "xanchor": "right", "x": 0.99},
        margin={"l": 70, "r": 20, "t": 20, "b": 70},
    )

    if normalize_y:
        fig.update_yaxes(title="Completed Workload", tickformat=".0%")
    else:
        fig.update_yaxes(title="Shots Completed")

    if common_start:
        fig.update_xaxes(tickformat="%H:%M:%S.%f")

    return fig
