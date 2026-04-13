# This code is part of Qiskit.
#
# (C) Copyright IBM 2026.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Function to visualize chunk timings from a :class:`~.QuantumProgramResult`."""

from __future__ import annotations

from itertools import cycle
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING
from collections.abc import Iterable

from ..quantum_program.quantum_program_result import ChunkTimings, ChunkSpan
from .utils import plotly_module

if TYPE_CHECKING:
    from plotly.graph_objects import Figure as PlotlyFigure


_HOVER_HEADER = "<br>".join(
    [
        "<b>{name}[{idx}]</b>",
        "<b>&nbsp;&nbsp;&nbsp;Start:</b> {start:%Y-%m-%d %H:%M:%S.%f}",
        "<b>&nbsp;&nbsp;&nbsp;Stop:</b> {stop:%Y-%m-%d %H:%M:%S.%f}",
        "<b>&nbsp;&nbsp;&nbsp;Duration:</b> {duration:.4g}s",
        "<b>&nbsp;&nbsp;&nbsp;Size:</b> {size}",
        "<b>&nbsp;&nbsp;&nbsp;Parts ({n_parts}):</b>",
    ]
)
_HOVER_PART = "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;item[{idx_item}]: {size}"
_HOVER_ELLIPSIS = "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;..."
_PARTS_LIMIT = 10


def _apply_tz(dt: datetime, tz: timezone | None) -> datetime:
    """Convert a datetime (assumed UTC if naive) to the given timezone, stripped of tzinfo.

    Args:
        dt: The datetime to convert. Treated as UTC if timezone-naive.
        tz: Target timezone. ``None`` means the local system timezone.

    Returns:
        A timezone-naive datetime in the target timezone.
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(tz=tz).replace(tzinfo=None)


def _format_hover(name: str, idx: int, chunk: ChunkSpan, tz: timezone | None) -> str:
    chunk_size = sum(p.size for p in chunk.parts)
    duration = (chunk.stop - chunk.start).total_seconds()
    lines = [
        _HOVER_HEADER.format(
            name=name,
            idx=idx,
            start=_apply_tz(chunk.start, tz),
            stop=_apply_tz(chunk.stop, tz),
            duration=duration,
            size=chunk_size,
            n_parts=len(chunk.parts),
        )
    ]
    for part in chunk.parts[:_PARTS_LIMIT]:
        lines.append(_HOVER_PART.format(idx_item=part.idx_item, size=part.size))
    if len(chunk.parts) > _PARTS_LIMIT:
        lines.append(_HOVER_ELLIPSIS)
    return "<br>".join(lines)


def _get_id(ct: ChunkTimings, multiple: bool) -> str:
    return f"<{hex(id(ct))}>" if multiple else ""


def draw_chunk_timings(
    *chunk_timings: ChunkTimings,
    names: str | Iterable[str] | None = None,
    common_start: bool = False,
    normalize_y: bool = False,
    line_width: int = 4,
    show_legend: bool | None = None,
    tz: timezone | None = None,
) -> PlotlyFigure:
    """Draw one or more :class:`~.ChunkTimings` on a bar plot.

    Each chunk corresponds to a single execution window on the backend. The y-axis represents
    cumulative work completed across chunks — in units of elements executed, or as a percentage
    if ``normalize_y=True``.

    When comparing multiple :class:`~.ChunkTimings` (e.g. from different jobs), use
    ``common_start=True`` to align traces at :math:`t=0` for direct comparison.

    .. note::
        For a simpler single-trace interface, call :meth:`~.ChunkTimings.draw` directly on the
        ``result.chunk_timings`` attribute.

    Args:
        chunk_timings: One or more :class:`~.ChunkTimings` collections,
            e.g. ``result.chunk_timings``.
        names: Name or names to assign to the respective ``chunk_timings``. When provided, a
            legend is shown by default.
        common_start: Whether to shift each collection's chunks so that its first chunk starts
            at :math:`t=0`. Useful for comparing timings from different jobs side by side.
        normalize_y: Whether to display the y-axis units as a percentage of work complete,
            rather than cumulative elements completed.
        line_width: The thickness of line segments.
        show_legend: Whether to show a legend. By default, shown only when ``names`` is provided.
        tz: The timezone to use for displaying times. ``None`` (default) uses the local system
            timezone. Pass ``datetime.timezone.utc`` to display times in UTC.

    Returns:
        A plotly figure.
    """
    go = plotly_module(".graph_objects")
    colors = plotly_module(".colors").qualitative.Plotly

    fig = go.Figure()

    # resolve names and legend visibility
    all_names: list[str] = []
    if names is None:
        show_legend = False if show_legend is None else show_legend
    else:
        show_legend = True if show_legend is None else show_legend
        if isinstance(names, str):
            all_names = [names]
        else:
            all_names.extend(names)

    # fill in default names for any without an explicit one
    multiple = len(chunk_timings) > 1
    all_names.extend(
        f"ChunkTimings{_get_id(ct, multiple)}" for ct in chunk_timings[len(all_names) :]
    )

    for ct, color, name in zip(chunk_timings, cycle(colors), all_names):
        if not ct:
            continue

        sorted_chunks = sorted(enumerate(ct), key=lambda x: x[1].start)

        offset = timedelta()
        if common_start:
            first_start = _apply_tz(sorted_chunks[0][1].start, tz)
            offset = first_start - datetime(year=1970, month=1, day=1)

        total_size = sum(sum(p.size for p in c.parts) for c in ct) if normalize_y else 1
        y_value = 0.0
        x_data = []
        y_data = []
        text_data = []

        for idx, chunk in sorted_chunks:
            chunk_size = sum(p.size for p in chunk.parts)
            y_value += chunk_size / total_size
            text = _format_hover(name, idx, chunk, tz)
            x_data.extend(
                [_apply_tz(chunk.start, tz) - offset, _apply_tz(chunk.stop, tz) - offset, None]
            )
            y_data.extend([y_value, y_value, None])
            text_data.extend([text] * 3)

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

    fig.update_layout(
        xaxis={"title": "Time", "type": "date"},
        showlegend=show_legend,
        legend={"yanchor": "bottom", "y": 0.01, "xanchor": "right", "x": 0.99},
        margin={"l": 70, "r": 20, "t": 20, "b": 70},
    )

    if normalize_y:
        fig.update_yaxes(title="Completed Workload", tickformat=".0%")
    else:
        fig.update_yaxes(title="Elements Completed")

    if common_start:
        fig.update_xaxes(tickformat="%H:%M:%S.%f")

    return fig
