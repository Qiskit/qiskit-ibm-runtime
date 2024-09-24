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

from __future__ import annotations

from typing import Union
from numpy.typing import ArrayLike
import numpy as np

from qiskit.primitives.containers import PubResult, DataBin

# Type alias
DebuggerResultLike = Union["DebuggerResult", PubResult, DataBin]
ScalarLike = Union[int, float]


SUPPORTED_OPERATIONS = ["add", "mul", "sub", "truediv", "radd", "rmul", "rsub", "rtruediv"]


class DebuggerResult:
    r"""A class to store the results of the ``Debugger``.

    It allows performing mathematical operations with other objects of type
    :class:`.~DebuggerResultLike`, such as ``+``, ``-``, ``*``, ``/``, and ``**``.

    Args:
        vals: The values in this :class:`.~DebuggerResult`.
    """

    def __init__(self, vals: ArrayLike) -> None:
        self._vals = np.array(vals, dtype=float)

    @property
    def vals(self) -> np.ndarray:
        r"""The values in this :class:`.~DebuggerResult`."""
        return self._vals

    def __pow__(self, p: ScalarLike) -> DebuggerResult:
        return DebuggerResult(self._vals**p)

    # def __add__(self, other: Union[DebuggerResultLike, ScalarLike]) -> DebuggerResult:
    #     return self._coerced_operation(other, "__add__")

    # def __mul__(self, other: Union[DebuggerResultLike, ScalarLike]) -> DebuggerResult:
    #     return self._coerced_operation(other, "__mul__")

    # def __sub__(self, other: Union[DebuggerResultLike, ScalarLike]) -> DebuggerResult:
    #     return self._coerced_operation(other, "__sub__")

    # def __truediv__(self, other: Union[DebuggerResultLike, ScalarLike]) -> DebuggerResult:
    #     return self._coerced_operation(other, "__truediv__")

    # def __radd__(self, other: Union[DebuggerResultLike, ScalarLike]) -> DebuggerResult:
    #     return self._coerced_operation(other, "__radd__")

    # def __rmul__(self, other: Union[DebuggerResultLike, ScalarLike]) -> DebuggerResult:
    #     return self._coerced_operation(other, "__rmul__")

    # def __rsub__(self, other: Union[DebuggerResultLike, ScalarLike]) -> DebuggerResult:
    #     return self._coerced_operation(other, "__rsub__")

    # def __rtruediv__(self, other: Union[DebuggerResultLike, ScalarLike]) -> DebuggerResult:
    #     return self._coerced_operation(other, "__rtruediv__")

    def __repr__(self) -> str:
        return f"DebuggerResult(vals={repr(self.vals)})"


# Initialize
for op_name in SUPPORTED_OPERATIONS:

    def _coerced_operation(
        this: DebuggerResult, other: Union[ScalarLike, DebuggerResult], op_name: str = op_name
    ) -> DebuggerResult:
        r"""Coerces ``other`` to a compatible format and applies ``__op_name__`` to ``self`` and ``other``."""
        if not isinstance(other, ScalarLike):
            if isinstance(other, DebuggerResult):
                other = other.vals
            elif isinstance(other, PubResult):
                other = other.data.evs
            elif isinstance(other, DataBin):
                try:
                    other = other.evs
                except AttributeError:
                    raise ValueError(
                        f"Cannot apply operator {'__{op_name}__'} between 'DebuggerResult' and"
                        "'DataBin' that has no attribute ``evs``."
                    )
            else:
                raise ValueError(
                    f"Cannot apply operator {'__{op_name}__'} to objects of type 'DebuggerResult' and '{other.__class__}'."
                )
        return DebuggerResult(getattr(this.vals, f"__{op_name}__")(other))

    setattr(
        DebuggerResult,
        f"__{op_name}__",
        _coerced_operation,
    )
