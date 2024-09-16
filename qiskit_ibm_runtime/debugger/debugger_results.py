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

""" A class to store debugger results.
"""

from typing import Union
from numpy.typing import NDArray

from qiskit.primitives.containers import PubResult, DataBin

# Type alias
DebuggerResultLike = Union["DebuggerResult", PubResult, DataBin]


class DebuggerResult:
    r"""A class to store the results of the ``Debugger``.

    It allows performing mathematical operations with other objects of type
    :class:`.~DebuggerResultLike`, such as ``+``, ``-``, ``*``, ``/``, and ``**``.
    """

    def __init__(self, vals: NDArray) -> None:
        self._vals = vals

    @property
    def vals(self) -> NDArray:
        return self._vals

    def __add__(self, other: DebuggerResultLike) -> "DebuggerResult":
        other = _coerce_result(other)
        return DebuggerResult(self.vals + other.vals)

    def __div__(self, other: DebuggerResultLike) -> "DebuggerResult":
        other = _coerce_result(other)
        return DebuggerResult(self.vals / other.vals)

    def __mul__(self, other: DebuggerResultLike) -> "DebuggerResult":
        other = _coerce_result(other)
        return DebuggerResult(self.vals * other.vals)

    def __pow__(self, p: float) -> "DebuggerResult":
        return DebuggerResult(self._vals**p)

    def __sub__(self, other: DebuggerResultLike) -> "DebuggerResult":
        other = _coerce_result(other)
        return DebuggerResult(self.vals - other.vals)

    def __radd__(self, other: DebuggerResultLike) -> "DebuggerResult":
        other = _coerce_result(other)
        return self + other

    def __rdiv__(self, other: DebuggerResultLike) -> "DebuggerResult":
        other = _coerce_result(other)
        return self / other

    def __rmul__(self, other: DebuggerResultLike) -> "DebuggerResult":
        other = _coerce_result(other)
        return self * other

    def __rsub__(self, other: DebuggerResultLike) -> "DebuggerResult":
        other = _coerce_result(other)
        return self - other

    def __repr__(self) -> str:
        return f"DebuggerResult(vals={repr(self.vals)})"


def _coerce_result(result: DebuggerResultLike) -> DebuggerResult:
    r"""
    A helper method to coerce turn a ``DebuggerResultLike`` object into a ``DebuggerResult`` one.
    """
    if isinstance(result, PubResult):
        result = DebuggerResult(result.data.evs)
    elif isinstance(result, DataBin):
        result = DebuggerResult(result.evs)

    if isinstance(result, DebuggerResult):
        return result
    raise ValueError(
        f"Object of type '{result.__class__}' cannot be coerced into a ``DebuggerResult`` object."
    )
