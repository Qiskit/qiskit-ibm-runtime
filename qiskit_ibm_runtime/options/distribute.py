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

from typing import Generic, Sequence, TypeVar

T = TypeVar("T")


class Distribute(Generic[T], list):
    """Distribute option values across PUBs."""

    def __init__(self, *args: Sequence[T]):
        super().__init__(args)

    def __repr__(self):
        return f"Distribute({', '.join(map(str, self))})"
