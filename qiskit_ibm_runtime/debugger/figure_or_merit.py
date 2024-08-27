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

"""A debugger."""

from __future__ import annotations
from abc import ABC, abstractmethod
import numpy as np
from typing import Any

from qiskit.primitives.containers import PrimitiveResult


class FOM(ABC):
    r"""Base class for the figures of merit used when comparing results through the debugger."""

    def __new__(cls, result1: PrimitiveResult, result2: PrimitiveResult):
        # Instead of returning an instance of FOM, return the result of the `__call__` method.
        # This allows doing, e.g., `Ratio(x, y)` instead of having to do `Ratio()(x, y)`.
        instance = super().__new__(cls)
        return instance.__call__(result1, result2)

    @abstractmethod
    def call(self, result1: PrimitiveResult, result2: PrimitiveResult) -> Any:
        r"""
        The calculation performed by this figure of merit to compute two results.
        """
        raise NotImplementedError()

    def __call__(self, result1: PrimitiveResult, result2: PrimitiveResult) -> Any:
        return self.call(result1, result2)

    def __repr__(self) -> str:
        return f"{self.__class__}({self.name})"


class Ratio(FOM):
    r"""A :class:`.~FOM` that computes the ratio ``result1/result2`` between two primitive results.

    It returns ``0`` when it encounters a ``0`` in the denominator.
    """

    def call(self, result1: PrimitiveResult, result2: PrimitiveResult):
        ret = []
        for r1, r2 in zip(result1, result2):
            ret.append(
                np.divide(
                    r1.data.evs,
                    r2.data.evs,
                    out=np.zeros_like(r1.data.evs, dtype=float),
                    where=np.array(r2.data.evs) != 0,
                ).tolist()
            )

        return ret
