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

from typing import TypeAlias
from numpy.typing import NDArray


DataTree: TypeAlias = (
    list["DataTree"] | NDArray[float] | dict[str, "DataTree"] | str | float | int | bool | None,
) # type: ignore
"""Arbitrary nesting of lists and dicts with typed leaves."""
