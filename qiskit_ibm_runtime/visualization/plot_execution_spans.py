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

from functools import partial
from typing import TYPE_CHECKING

import plotly.graph_objects as go
import numpy as np

if TYPE_CHECKING:
    from ..execution_span import ExecutionSpans

HOVER_TEMPLATE = "<br>".join(
    [
        "<b>ExecutionSpans{id}[{idx}]</b>",
        "<b>&nbsp;&nbsp;&nbsp;Start:</b> {span.start:%Y-%m-%d %H:%M:%S.%f}",
        "<b>&nbsp;&nbsp;&nbsp;Stop:</b> {span.stop:%Y-%m-%d %H:%M:%S.%f}",
        "<b>&nbsp;&nbsp;&nbsp;Size:</b> {span.size}",
        "<b>&nbsp;&nbsp;&nbsp;Pub Indexes:</b> {idxs}",
    ]
)


def _get_idxs(span, limit=10):
    if len(idxs := span.pub_idxs) <= limit:
        return str(idxs)
    else:
        return f"[{', '.join(map(str, idxs[:limit]))}, ...]"


def _get_id(span, multiple):
    return f"<{hex(id(span))}>" if multiple else ""


def plot_execution_spans(*list_of_spans: ExecutionSpans, common_start: bool = False) -> go.Figure:
    """Plot one or more :class:`~.ExecutionSpans` on a bar plot.

    Args:
        list_of_spans: One or more :class:`~.ExecutionSpans`.
        common_start: Whether to shift all collections of spans so that their first span's start is
            at :math:`t=0`.

    Returns:
        A plotly figure.
    """
    fig = go.Figure()

    get_id = partial(_get_id, multiple=len(list_of_spans) > 1)

    for spans in list_of_spans:
        if not spans:
            continue
        spans = spans.sort(inplace=False)

        starts = np.array([span.start.replace(tzinfo=None) for span in spans], dtype=np.datetime64)
        stops = np.array([span.stop.replace(tzinfo=None) for span in spans], dtype=np.datetime64)
        # plotly wants durations to be numeric in units of ms
        durations = (stops - starts) / np.timedelta64(1, "ms")
        total_sizes = np.cumsum([span.size for span in spans])

        if common_start:
            # plotly doesn't natively support using date formatting with time deltas,
            # so the commonly recommended hack is to plot absolute times past the epoch
            # but format the ticks to not include the year
            offsets = starts - np.datetime64(spans.start.replace(tzinfo=None))
            starts = np.datetime64("1970-01-01") + offsets

        texts = [
            HOVER_TEMPLATE.format(span=span, idx=idx, idxs=_get_idxs(span), id=get_id(span))
            for idx, span in enumerate(spans)
        ]

        # Add a trace for each time segment
        fig.add_trace(
            go.Bar(
                y=list(map(int, total_sizes)),
                x=durations,
                orientation="h",
                width=0.4,
                base=starts,
                text=texts,
                hoverinfo="text",
                textposition="none",
            )
        )

        xaxis_format = dict(title="Time", type="date")
        if common_start:
            xaxis_format["tickformat"] = "%H:%M:%S.%f"

    # Update layout for better visualization
    fig.update_layout(
        xaxis=xaxis_format,
        barmode="group",
        yaxis=dict(title="Execution Spans", type="category"),
        bargap=0.3,
        showlegend=False,
        margin=dict(l=70, r=20, t=20, b=70),
    )

    return fig
