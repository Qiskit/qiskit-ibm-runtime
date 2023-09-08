# This code is part of Qiskit.
#
# (C) Copyright IBM 2023.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Twirling options."""

from typing import Optional
from dataclasses import dataclass

from .utils import _flexible


@_flexible
@dataclass
class TwirlingOptions:
    """Twirling options.

    Args:
        gates: Whether to apply gate twirling.
            By default, gate twirling is enabled for resilience level >0.

        measure: Whether to apply measurement twirling.
            By default, measurement twirling is enabled for resilience level >0.
    """

    gates: Optional[bool] = None
    measure: Optional[bool] = None
