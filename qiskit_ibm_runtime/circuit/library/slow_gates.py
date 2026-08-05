# This code is part of Qiskit.
#
# (C) Copyright IBM 2026.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Slow gate instructions."""

from qiskit.circuit import Instruction


class XSlowGate(Instruction):
    """A class for a ``xslow`` instruction."""

    def __init__(self, name="x_slow") -> None:
        super().__init__(name, 1, 0, [])


class CZSlowGate(Instruction):
    """A class for a ``cz_slow`` instruction."""

    def __init__(self, name: str = "cz_slow", label: str | None = None) -> None:
        super().__init__(name, 2, 0, [], label=label)
