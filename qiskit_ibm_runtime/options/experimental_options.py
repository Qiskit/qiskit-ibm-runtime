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

"""Experimental options."""

from typing import Union, List
from pydantic import Field

from .utils import Dict, Unset, UnsetType, flexible_primitive_dataclass


@flexible_primitive_dataclass
class ExperimentalZNEOptions:
    amplifier: Union[UnsetType, str] = Unset
    return_all_extrapolated: Union[UnsetType, bool] = Unset
    return_unextrapolated: Union[UnsetType, bool] = Unset
    extrapolated_noise_factors: Union[float, List[float]] = 0
@flexible_primitive_dataclass
class ExperimentalResilienceOptions:
    zne: Union[ExperimentalZNEOptions, Dict] = Field(default_factory=ExperimentalZNEOptions)
@flexible_primitive_dataclass
class ExperimentalOptionsV2:
    """Experimental options for V2 primitives.

    Args:

    """
    resilience: Union[ExperimentalResilienceOptions, Dict] = Field(default_factory=ExperimentalResilienceOptions)

