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

"""Probabalistic error cancellation mitigation options."""

from typing import Union, Literal

from .utils import Unset, UnsetType, primitive_dataclass, make_constraint_validator


@primitive_dataclass
class PecOptions:
    """Probabalistic error cancellation mitigation options.

    Args:
        max_overhead: The maximum circuit sampling overhead allowed, or
            ``None`` for no maximum. Default: 100.

        noise_gain: The amount by which to scale the noise, where:

            * A value of one corresponds to attempting to remove all of the noise.
            * A value greater than one corresponds to injecting noise.
            * A value between 0 and 1 corresponds to partially removing the noise.

            If "auto", the value will be chosen automatically
            based on the input PUBs. Default: "auto".
    """

    max_overhead: Union[UnsetType, float, None] = Unset
    noise_gain: Union[UnsetType, float, Literal["auto"]] = Unset

    _gt0 = make_constraint_validator("max_overhead", "noise_gain", gt=0)
