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

from typing import Iterable, TypeVar, Union, overload, Tuple, Dict, List
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
        return (self.stop - self.start).seconds

    def contains_pub(self, pub_idx: Union[int, Iterable[int]]) -> bool:
        """Returns if a pub is contained"""
        pub_idx = {pub_idx} if isinstance(pub_idx, int) else set(pub_idx)
        return not pub_idx.isdisjoint(self.data_slices)

    def filter_by_pub(self, pub_idx: Union[int, Iterable[int]]) -> "ExecutionSpan":
        """Returns an ExecutionSpan filtered by pub-"""
        pub_idx = {pub_idx} if isinstance(pub_idx, int) else set(pub_idx)
        slices = {idx: sl for idx, sl in self.data_slices.items() if idx in pub_idx}
        return ExecutionSpan(self.start, self.stop, slices)


class ExecutionSpanCollection:
    """A collection of timings for the PUB result."""

    def __init__(self, spans: Iterable[ExecutionSpan]):
        self._spans = spans

    def __len__(self) -> int:
        return len(list(self._spans))

    @overload
    def __getitem__(self, idxs: int) -> ExecutionSpan:
        ...

    @overload
    def __getitem__(self, idxs: Union[slice, List[int]]) -> "ExecutionSpanCollection":
        ...
        
    def __getitem__(self, idxs):
        if isinstance(idxs, int):
            return self._spans[idxs]
        if isinstance(idxs, slice):
            return ExecutionSpanCollection(self._spans[idxs])
        return ExecutionSpanCollection([self._spans[idx] for idx in idxs])

    def __iter__(self):
        return iter(self._spans)

    @property
    def start(self) -> datetime:
        """The start time of the entire collection, in UTC."""
        return min(span.start for span in self._spans)

    @property
    def stop(self) -> datetime:
        """The stop time of the entire collection, in UTC."""
        return max(span.stop for span in self._spans)

    def plot(self):
        """Show a timing diagram"""
        pass
