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

"""DressingMode"""

from enum import Enum
from typing import Literal, Union


class DressingMode(str, Enum):
    """Which side of a box to anchor the dressing gates to."""

    LEFT = "left"
    RIGHT = "right"


DressingLiteral = Union[DressingMode, Literal["left", "right"]]
"""Allowed box dressing modes.

 * ``left``: Gate collection templates are placed on the left side of boxes.
 * ``right``: Gate collection templates are placed on the right side of boxes.

A gate collection template is a fixed, parametric circuit fragment, such as
:math:`R_Z(\\dot)\\sqrt{X}R_Z(\\dot)\\sqrt{X}R_Z(\\dot)`, that is applied to all subsystems
of a box. The fragment is used to effectively collect and implement randomly sampled virtual gates,
and also to absorb nearby compatible gates within the box.
"""
