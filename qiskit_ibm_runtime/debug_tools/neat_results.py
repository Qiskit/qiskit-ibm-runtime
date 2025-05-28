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

"""A class to store Neat results."""

from __future__ import annotations

from typing import Iterable, Union
from numpy.typing import ArrayLike
import numpy as np

from qiskit.primitives.containers import PubResult, DataBin

# Type aliases
NeatPubResultLike = Union["NeatPubResult", PubResult, DataBin]
ScalarLike = Union[int, float]


class NeatPubResult:
    r"""A class to store the PUB results of :class:`.~Neat`.

    It allows performing mathematical operations (``+``, ``-``, ``*``, ``/``, ``abs``, and ``**``)
    with other objects of type :class:`.~NeatPubResultLike` and with scalars.

    .. code::python

        from qiskit_ibm_runtime.debug_tools import NeatPubResult

        res = NeatPubResult([[1, 2], [3, 4]])

        # this returns NeatPubResult([[3, 4], [5, 6]])
        res + 2

        # this returns NeatPubResult([[3, 8], [15, 24]])
        res * (res + 2)

    Args:
        vals: The values in this :class:`.~NeatPubResult`.
    """

    def __init__(self, vals: ArrayLike) -> None:
        self._vals = np.array(vals, dtype=float)

    @property
    def vals(self) -> np.ndarray:
        r"""The values in this result."""
        return self._vals

    def _coerced_operation(
        self, other: Union[ScalarLike, NeatPubResultLike], op_name: str
    ) -> NeatPubResult:
        r"""
        Coerces ``other`` to a compatible format and applies ``op_name`` to ``self`` and ``other``.
        """
        if not isinstance(other, (int, float)):
            if isinstance(other, NeatPubResult):
                other = other.vals
            elif isinstance(other, PubResult):
                other = other.data.evs
            elif isinstance(other, DataBin):
                try:
                    other = other.evs
                except AttributeError:
                    raise ValueError(
                        f"Cannot apply operator '{op_name}' between 'NeatPubResult' and 'DataBin'"
                        " that has no attribute ``evs``."
                    )
            else:
                raise ValueError(
                    f"Cannot apply operator '{op_name}' to objects of type 'NeatPubResult' and "
                    f"'{other.__class__}'."
                )
        return NeatPubResult(getattr(self.vals, f"{op_name}")(other))

    def __abs__(self) -> NeatPubResult:
        return NeatPubResult(np.abs(self.vals))

    def __add__(self, other: Union[ScalarLike, NeatPubResultLike]) -> NeatPubResult:
        return self._coerced_operation(other, "__add__")

    def __mul__(self, other: Union[ScalarLike, NeatPubResultLike]) -> NeatPubResult:
        return self._coerced_operation(other, "__mul__")

    def __sub__(self, other: Union[ScalarLike, NeatPubResultLike]) -> NeatPubResult:
        return self._coerced_operation(other, "__sub__")

    def __truediv__(self, other: Union[ScalarLike, NeatPubResultLike]) -> NeatPubResult:
        return self._coerced_operation(other, "__truediv__")

    def __radd__(self, other: Union[ScalarLike, NeatPubResultLike]) -> NeatPubResult:
        return self._coerced_operation(other, "__radd__")

    def __rmul__(self, other: Union[ScalarLike, NeatPubResultLike]) -> NeatPubResult:
        return self._coerced_operation(other, "__rmul__")

    def __rsub__(self, other: Union[ScalarLike, NeatPubResultLike]) -> NeatPubResult:
        return self._coerced_operation(other, "__rsub__")

    def __rtruediv__(self, other: Union[ScalarLike, NeatPubResultLike]) -> NeatPubResult:
        return self._coerced_operation(other, "__rtruediv__")

    def __pow__(self, p: ScalarLike) -> NeatPubResult:
        return NeatPubResult(self._vals**p)

    def __repr__(self) -> str:
        return f"NeatPubResult(vals={repr(self.vals)})"


class NeatResult:
    """A container for multiple :class:`~.NeatPubResult` objects.

    Args:
        pub_results: An iterable of :class:`~.NeatPubResult` objects.
    """

    def __init__(self, pub_results: Iterable[NeatPubResult]) -> None:
        self._pub_results = list(pub_results)

    def __getitem__(self, index: int) -> NeatPubResult:
        return self._pub_results[index]

    def __len__(self) -> int:
        return len(self._pub_results)

    def __repr__(self) -> str:
        return f"NeatResult({self._pub_results})"

    def __iter__(self) -> Iterable[NeatPubResult]:
        return iter(self._pub_results)
