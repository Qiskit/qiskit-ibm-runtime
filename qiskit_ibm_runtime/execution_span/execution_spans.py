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

"""ExecutionSpans"""

from __future__ import annotations

from datetime import datetime
from typing import overload, Iterable, Iterator, TYPE_CHECKING

from .execution_span import ExecutionSpan

if TYPE_CHECKING:
    from plotly.graph_objects import Figure as PlotlyFigure


class ExecutionSpans:
    """A collection of timings for pub results.

    This class is a list-like containing :class:`~.ExecutionSpan`\\s, where each execution span
    represents a time window of data collection, and contains a reference to exactly which of the
    data were collected during the window.

    .. code::python

        spans = sampler_job.result().metadata["execution"]["execution_spans"]

        for span in spans:
            print(span)

    It is possible for distinct time windows to overlap. This is not because a QPU was performing
    multiple executions at once, but is instead an artifact of certain classical processing
    that may happen concurrently with quantum execution. The guarantee being made is that the
    referenced data definitely occurred in the reported execution span, but not necessarily that
    the limits of the time window are as tight as possible.
    """

    def __init__(self, spans: Iterable[ExecutionSpan]):
        self._spans = list(spans)

    def __len__(self) -> int:
        return len(self._spans)

    @overload
    def __getitem__(self, idxs: int) -> ExecutionSpan: ...

    @overload
    def __getitem__(self, idxs: slice | list[int]) -> "ExecutionSpans": ...

    def __getitem__(self, idxs: int | slice | list[int]) -> ExecutionSpan | "ExecutionSpans":
        if isinstance(idxs, int):
            return self._spans[idxs]
        if isinstance(idxs, slice):
            return ExecutionSpans(self._spans[idxs])
        return ExecutionSpans(self._spans[idx] for idx in idxs)

    def __iter__(self) -> Iterator[ExecutionSpan]:
        return iter(self._spans)

    def __repr__(self) -> str:
        return f"ExecutionSpans({repr(self._spans)})"

    def __eq__(self, other: object) -> bool:
        return isinstance(other, ExecutionSpans) and self._spans == other._spans

    @property
    def pub_idxs(self) -> list[int]:
        """Which pubs, by index, have dependence on one or more execution spans present."""
        return sorted({idx for span in self for idx in span.pub_idxs})

    @property
    def start(self) -> datetime:
        """The start time of the entire collection, in UTC."""
        return min(span.start for span in self)

    @property
    def stop(self) -> datetime:
        """The stop time of the entire collection, in UTC."""
        return max(span.stop for span in self)

    @property
    def duration(self) -> float:
        """The total duration of this collection, in seconds."""
        return (self.stop - self.start).total_seconds()

    def filter_by_pub(self, pub_idx: int | Iterable[int]) -> "ExecutionSpans":
        """Return a new set of spans where each one has been filtered to the specified pubs.

        See also :meth:~.ExecutionSpan.filter_by_pub`.

        Args:
            pub_idx: One or more pub indices to filter.
        """
        return ExecutionSpans(span.filter_by_pub(pub_idx) for span in self)

    def sort(self, inplace: bool = True) -> "ExecutionSpans":
        """Return the same execution spans, sorted.

        Sorting is done by the :attr:`~.ExecutionSpan.start` timestamp of each execution span.

        Args:
            inplace: Whether to sort this instance in place, or return a copy.

        Returns:
            This instance if ``inplace``, a new instance otherwise, sorted.
        """
        obj = self if inplace else ExecutionSpans(self)
        obj._spans.sort()
        return obj

    def draw(
        self, name: str = None, normalize_y: bool = False, line_width: int = 4
    ) -> PlotlyFigure:
        """Draw these execution spans.

        .. note::
            To draw multiple sets of execution spans at once, for example coming from multiple
            jobs, consider calling :meth:`~qiskit_ibm_runtime.visualization.draw_execution_spans`
            directly.

        Args:
            name: The name of this set of spans.
            normalize_y: Whether to display the y-axis units as a percentage of work
                complete, rather than cumulative shots completed.
            line_width: The thickness of line segments.

        Returns:
            A plotly figure.
        """
        # pylint: disable=import-outside-toplevel, cyclic-import
        from ..visualization import draw_execution_spans

        return draw_execution_spans(
            self, normalize_y=normalize_y, line_width=line_width, names=name
        )
