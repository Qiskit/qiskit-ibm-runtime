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

"""SliceSpan"""

from __future__ import annotations

from datetime import datetime
import math
from typing import Iterable

import numpy as np
import numpy.typing as npt

from .execution_span import ExecutionSpan, ShapeType


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
