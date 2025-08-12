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

"""TwirledSliceSpan"""

from __future__ import annotations

from datetime import datetime
from typing import Iterable, Mapping

import math
import numpy as np
import numpy.typing as npt

from .execution_span import ExecutionSpan, ShapeType


class TwirledSliceSpan(ExecutionSpan):
    """An :class:`~.ExecutionSpan` for data stored in a sliceable format when twirling.

    This type of execution span references pub result data that came from a twirled sampler
    experiment which was executed by either prepending or appending an axis to parameter values
    to account for twirling. Concretely, ``data_slices`` is a map from pub slices to tuples
    ``(twirled_shape, at_front, shape_slice, shots_slice)`` where

    * ``twirled_shape`` is the shape tuple including a twirling axis, and where the last
      axis is shots per randomization,
    * ``at_front`` is whether ``num_randomizations`` is at the front of the tuple, as
      opposed to right before the ``shots`` axis at the end,
    * ``shape_slice`` is a slice of an array of shape ``twirled_shape[:-1]``, flattened,
    * and ``shots_slice`` is a slice of ``twirled_shape[-1]``.

    Args:
        start: The start time of the span, in UTC.
        stop: The stop time of the span, in UTC.
        data_slices: A map from pub indices to length-4 tuples described above.
    """

    def __init__(
        self,
        start: datetime,
        stop: datetime,
        data_slices: Mapping[int, tuple[ShapeType, bool, slice, slice]],
    ):
        super().__init__(start, stop)
        self._data_slices = data_slices

    def __eq__(self, other: object) -> bool:
        return isinstance(other, TwirledSliceSpan) and (
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
        for data_slice in self._data_slices.values():
            shape, _, shape_sl, shots_sl = data_slice[:4]
            size += len(range(math.prod(shape[:-1]))[shape_sl]) * len(range(shape[-1])[shots_sl])
        return size

    def mask(self, pub_idx: int) -> npt.NDArray[np.bool_]:
        # This function assumes that the data slices don't contain information
        # about pub shots, therefore `TwirledSliceSpanV2` must override it
        if pub_idx not in self._data_slices:
            raise KeyError(f"Pub {pub_idx} is not included in the span.")

        shape, at_front, shape_sl, shots_sl = self._data_slices[pub_idx][:4]
        mask = np.zeros(shape, dtype=np.bool_)
        mask.reshape((np.prod(shape[:-1], dtype=int), shape[-1]))[(shape_sl, shots_sl)] = True

        if at_front:
            # if the first axis is over twirling samples, push them right before shots
            ndim = len(shape)
            mask = mask.transpose((*range(1, ndim - 1), 0, ndim - 1))
            shape = shape[1:-1] + shape[:1] + shape[-1:]

        # merge twirling axis and shots axis before returning
        return mask.reshape((*shape[:-2], math.prod(shape[-2:])))

    def filter_by_pub(self, pub_idx: int | Iterable[int]) -> "TwirledSliceSpan":
        pub_idx = {pub_idx} if isinstance(pub_idx, int) else set(pub_idx)
        slices = {idx: val for idx, val in self._data_slices.items() if idx in pub_idx}
        return type(self)(self.start, self.stop, slices)


class TwirledSliceSpanV2(TwirledSliceSpan):
    """An iteration of :class:`~.TwirledSliceSpan` that additionally stores the number of pub shots.

    This type of execution span references pub result data that came from a twirled sampler
    experiment which was executed by either prepending or appending an axis to parameter values
    to account for twirling. Concretely, ``data_slices`` is a map from pub slices to tuples
    ``(twirled_shape, at_front, shape_slice, shots_slice, pub_shots)``, where everything is as in
    :class:`~.TwirledSliceSpan`, but additionally:

    * ``pub_shots`` is the number of shots requested for the pub. It can be smaller than
      ``num_randomizations`` times ``shots_per_randomizations``, and the last axis of
      :meth:`.TwirledSliceSpan.mask` must be truncated, such that its length becomes
      equal to ``pub_shots``.

    Args:
        start: The start time of the span, in UTC.
        stop: The stop time of the span, in UTC.
        data_slices: A map from pub indices to length-5 tuples described above.
    """

    def __init__(
        self,
        start: datetime,
        stop: datetime,
        data_slices: Mapping[int, tuple[ShapeType, bool, slice, slice, int]],
    ):
        data_slices_no_shots = {idx: val[:4] for idx, val in data_slices.items()}
        self._pub_shots = {idx: val[4] for idx, val in data_slices.items()}
        super().__init__(start, stop, data_slices_no_shots)

    def mask(self, pub_idx: int) -> npt.NDArray[np.bool_]:
        return super().mask(pub_idx)[..., : self._pub_shots[pub_idx]]
