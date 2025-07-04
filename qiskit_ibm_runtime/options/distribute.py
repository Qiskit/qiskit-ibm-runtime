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

"Distribute." ""

from typing import Any, Generic, Iterable, TypeVar

import numpy as np

T = TypeVar("T")


class Distribute(Generic[T]):
    """Distribute option values across PUBs."""

    def __init__(self, *args: T):
        self.values = list(args)

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Distribute):
            return False
        if len(self) != len(other):
            return False
        for self_value, other_value in zip(self, other):
            if not np.array_equal(self_value, other_value):
                return False
        return True

    def __iter__(self) -> Iterable[T]:
        return iter(self.values)

    def __len__(self) -> int:
        return len(self.values)

    def __repr__(self) -> str:
        return f"Distribute({', '.join(map(str, self.values))})"
