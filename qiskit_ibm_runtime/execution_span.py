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

"""Execution span classes."""

from __future__ import annotations

import abc
from datetime import datetime
import math
from typing import overload, Iterable, Iterator, Tuple

import numpy as np
import numpy.typing as npt


# Python 3.8 does not recognize tuple[<something],
# in spite of `from __future__ import annotations`
ShapeType = Tuple[int, ...]
"""A shape tuple representing some nd-array shape."""


class ExecutionSpan(abc.ABC):
    """Abstract parent for classes that store an execution time span for a subset of job data.

    A pub is said to have dependence on an execution span if the corresponding execution includes
    data that forms any part of the pub's results.

    Execution spans are equality checkable, and they implement a comparison operator based on
    the tuple ``(start, stop)``, so can be sorted.

    Args:
        start: The start time of the span, in UTC.
        stop: The stop time of the span, in UTC.
    """

    def __init__(self, start: datetime, stop: datetime):
        self._start = start
        self._stop = stop

    @abc.abstractmethod
    def __eq__(self, other: object) -> bool:
        pass

    def __lt__(self, other: ExecutionSpan) -> bool:
        return (self.start, self.stop) < (other.start, other.stop)

    def __repr__(self) -> str:
        attrs = [
            f"start='{self.start:%Y-%m-%d %H:%M:%S}'",
            f"stop='{self.stop:%Y-%m-%d %H:%M:%S}'",
            f"size={self.size}",
        ]
        return f"{type(self).__name__}(<{', '.join(attrs)}>)"

    @property
    def duration(self) -> float:
        """The duration of this span, in seconds."""
        return (self.stop - self.start).total_seconds()

    @property
    @abc.abstractmethod
    def pub_idxs(self) -> list[int]:
        """Which pubs, by index, have dependence on this execution span."""

    @property
    def start(self) -> datetime:
        """The start time of the span, in UTC."""
        return self._start

    @property
    def stop(self) -> datetime:
        """The stop time of the span, in UTC."""
        return self._stop

    @property
    def size(self) -> int:
        """The total number of results with dependence on this execution span, across all pubs.

        This attribute is equivalent to the sum of the elements of all present :meth:`mask`\\s.
        For sampler results, it represents the total number of shots with dependence on this
        execution span.

        Combine this attribute with :meth:`filter_by_pub` to find the size of some particular pub:

        .. code:: python

            span.filter_by_pub(2).size

        """
        return sum(self.mask(pub_idx).sum() for pub_idx in self.pub_idxs)

    @abc.abstractmethod
    def mask(self, pub_idx: int) -> npt.NDArray[np.bool_]:
        """Return an array-valued mask specifying which parts of a pub result depend on this span.

        Args:
            pub_idx: The index of the pub to return a mask for.

        Returns:
            An array with the same shape as the pub data.
        """

    def contains_pub(self, pub_idx: int | Iterable[int]) -> bool:
        """Return whether the pub with the given index has data with dependence on this span.

        Args:
            pub_idx: One or more pub indices from the original primitive call.

        Returns:
            Whether there is dependence on this span.
        """
        pub_idx = {pub_idx} if isinstance(pub_idx, int) else set(pub_idx)
        return not pub_idx.isdisjoint(self.pub_idxs)

    @abc.abstractmethod
    def filter_by_pub(self, pub_idx: int | Iterable[int]) -> "ExecutionSpan":
        """Return a new span whose slices are filtered to the provided pub indices.

        For example, if this span contains slice information for pubs with indices 1, 3, 4 and
        ``[1, 4]`` is provided, then the span returned by this method will contain slice information
        for only those two indices, but be identical otherwise.

        Args:
            pub_idx: One or more pub indices from the original primitive call.

        Returns:
            A new filtered span.
        """


class SliceSpan(ExecutionSpan):
    """An :class:`~.ExecutionSpan` for data stored in a sliceable format.

    This type of execution span references pub result data by assuming that it is a sliceable
    portion of the (row major) flattened data. Therefore, for each pub dependent on this span, the
    constructor accepts a single :class:`slice` object, along with the corresponding shape of the
    data to be sliced.

    Args:
        start: The start time of the span, in UTC.
        stop: The stop time of the span, in UTC.
        data_slices: A map from pub indices to pairs ``(shape_tuple, slice)``.
    """

    def __init__(
        self, start: datetime, stop: datetime, data_slices: dict[int, tuple[ShapeType, slice]]
    ):
        super().__init__(start, stop)
        self._data_slices = data_slices

    def __eq__(self, other: object) -> bool:
        return isinstance(other, SliceSpan) and (
            self.start == other.start
            and self.stop == other.stop
            and self._data_slices == other._data_slices
        )

    @property
    def pub_idxs(self) -> list[int]:
        return sorted(self._data_slices)

    @property
    def size(self) -> int:
        size = 0
        for shape, sl in self._data_slices.values():
            size += len(range(math.prod(shape))[sl])
        return size

    def mask(self, pub_idx: int) -> npt.NDArray[np.bool_]:
        shape, sl = self._data_slices[pub_idx]
        mask = np.zeros(shape, dtype=np.bool_)
        mask.ravel()[sl] = True
        return mask

    def filter_by_pub(self, pub_idx: int | Iterable[int]) -> "SliceSpan":
        pub_idx = {pub_idx} if isinstance(pub_idx, int) else set(pub_idx)
        slices = {idx: val for idx, val in self._data_slices.items() if idx in pub_idx}
        return SliceSpan(self.start, self.stop, slices)


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
