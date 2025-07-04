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

"""Decomposition mode."""

from enum import StrEnum
from typing import Literal, Union, TypeAlias


class DecompositionMode(StrEnum):
    """How to decompose arbitrary single-qubit gates."""

    RZSX = "rzsx"
    """Decompose as rz-sx-rz-sx-rz."""

    RZRX = "rzrx"
    """Decompose as rz-rx-rz."""


DecompositionLiteral: TypeAlias = Union[DecompositionMode, Literal["rzsx", "rzrx"]]
"""Allowed box decomposition modes.

 * ``rzsx``: Box dressings are of the form
   :math:`R_Z(\\dot) \\sqrt{X} R_Z(\\dot) \\sqrt{X} R_Z(\\dot)`.
 * ``rzrx``: Box dressings are of the form :math:`R_Z(\\dot) R_X(\\dot) R_Z(\\dot)`.
"""
