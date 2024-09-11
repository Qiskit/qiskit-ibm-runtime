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

"""ExecutionSpan"""

from __future__ import annotations

import abc
from datetime import datetime
from typing import Iterable, Tuple

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
