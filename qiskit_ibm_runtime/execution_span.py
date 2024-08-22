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

from typing import Iterable, Union, overload, Tuple, Dict, List, Iterator, Sequence
from datetime import datetime
from dataclasses import dataclass


SliceType = Tuple[int, int]


@dataclass(frozen=True)
class ExecutionSpan:
    """Stores an execution time span for a subset of job data."""

    start: datetime
    """The start time of the span, in UTC."""

    stop: datetime
    """The stop time of the span, in UTC."""

    data_slices: Dict[int, SliceType]
    r"""Which data have dependence on this execution span.

    Data from the primitives are array-based, with every field in a 
    :class:`~PubResult`\s :class:`~.DataBin` sharing the same base shape.
    Therefore, the format of this field is a mapping from pub indexes to 
    the same format accepted by 
    NumPy slicing, where each value indicates which slice of each field in the
    data bin depend on raw data collected during this execution span.
    """

    @property
    def duration(self) -> float:
        """Return the duration"""
        return (self.stop - self.start).total_seconds()

    def contains_pub(self, pub_idx: Union[int, Iterable[int]]) -> bool:
        """Returns if a pub is contained"""
        pub_idx = {pub_idx} if isinstance(pub_idx, int) else set(pub_idx)
        return not pub_idx.isdisjoint(self.data_slices)

    def filter_by_pub(self, pub_idx: Union[int, Iterable[int]]) -> "ExecutionSpan":
        """Returns an ExecutionSpan filtered by pub"""
        pub_idx = {pub_idx} if isinstance(pub_idx, int) else set(pub_idx)
        slices = {idx: sl for idx, sl in self.data_slices.items() if idx in pub_idx}
        return ExecutionSpan(self.start, self.stop, slices)

    def to_tuple(self) -> Tuple:
        """Return span in the form of a tuple"""
        return (self.start, self.stop, self.data_slices)

    @classmethod
    def from_tuple(cls, span_tuple: Tuple) -> "ExecutionSpan":
        """Construct a span from a tuple"""
        return ExecutionSpan(*list(span_tuple))

    def __str__(self) -> str:
        return str(self.to_tuple())


class ExecutionSpanSet:
    """A collection of timings for the PUB result."""

    def __init__(self, spans: Sequence[ExecutionSpan]):
        self._spans = spans

    def __len__(self) -> int:
        return len(list(self._spans))

    @overload
    def __getitem__(self, idxs: int) -> ExecutionSpan: ...

    @overload
    def __getitem__(self, idxs: Union[slice, List[int]]) -> "ExecutionSpanSet": ...

    def __getitem__(
        self, idxs: Union[int, slice, List[int]]
    ) -> Union[ExecutionSpan, "ExecutionSpanSet"]:
        if isinstance(idxs, int):
            return self._spans[idxs]
        if isinstance(idxs, slice):
            return ExecutionSpanSet(self._spans[idxs])
        return ExecutionSpanSet([self._spans[idx] for idx in idxs])

    def __iter__(self) -> Iterator[ExecutionSpan]:
        return iter(self._spans)

    def __str__(self) -> str:
        return str(self.to_list_of_tuples())

    def __eq__(self, other: object) -> bool:
        # TODO: consider changing to a dataclass
        if not isinstance(other, ExecutionSpanSet):
            return NotImplemented
        return self._spans == other._spans

    def to_list_of_tuples(self) -> List:
        """Return span set in the form of a list of tuples"""
        return [span.to_tuple() for span in self]

    @classmethod
    def from_list_of_tuples(cls, list_of_tuples: Sequence[Tuple]) -> "ExecutionSpanSet":
        """ "Construct span set from a list of tuples"""
        return ExecutionSpanSet(
            [ExecutionSpan.from_tuple(span_tuple) for span_tuple in list_of_tuples]
        )

    @property
    def start(self) -> datetime:
        """The start time of the entire collection, in UTC."""
        return min(span.start for span in self._spans)

    @property
    def stop(self) -> datetime:
        """The stop time of the entire collection, in UTC."""
        return max(span.stop for span in self)

    @property
    def duration(self) -> float:
        """Return the duration"""
        return (self.stop - self.start).total_seconds()

    def filter_by_pub(self, pub_idx: Union[int, Iterable[int]]) -> "ExecutionSpanSet":
        """Returns an ExecutionSpanSet filtered by pub"""
        return ExecutionSpanSet([span.filter_by_pub(pub_idx) for span in self])

    def plot(self) -> None:
        """Show a timing diagram"""
        raise NotImplementedError
