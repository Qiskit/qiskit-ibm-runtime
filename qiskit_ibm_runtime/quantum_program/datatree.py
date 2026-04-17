# This code is part of Qiskit.
#
# (C) Copyright IBM 2025.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""DataTree"""
from __future__ import annotations

from typing import Any
import numpy as np


from typing import TypeAlias
from numpy.typing import NDArray


DataTree: TypeAlias = (
    list["DataTree"] | dict[str, "DataTree"] | NDArray[float] | str | float | int | bool | None
)
"""Arbitrary nesting of lists and dicts with typed leaves."""


def is_datatree_compatible(data: Any) -> bool:
    """Check if data is compatible with DataTree format.

    DataTree is defined as: list["DataTree"] | dict[str, "DataTree"] | NDArray |
    str | float | int | bool | None

    Args:
        data: The data to check.

    Returns:
        True if data is compatible with DataTree format, False otherwise.
    """
    if data is None or isinstance(data, (str, bool, int, float, np.ndarray)):
        return True

    if isinstance(data, list):
        # Recursively check list elements
        return all(is_datatree_compatible(item) for item in data)

    if isinstance(data, dict):
        # Check dict keys are strings and recursively check values
        if not all(isinstance(key, str) for key in data.keys()):
            return False
        return all(is_datatree_compatible(value) for value in data.values())

    # Any other type is not compatible
    return False
