# This code is part of Qiskit.
#
# (C) Copyright IBM 2022.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Sampler options."""

from typing import Union, Literal

from pydantic import Field, field_validator

from .utils import Dict, Unset, UnsetType, skip_unset_validation
from .execution_options import ExecutionOptionsV2
from .twirling_options import TwirlingOptions
from .options import OptionsV2
from .utils import primitive_dataclass

DDSequenceType = Literal["XX", "XpXm", "XY4"]
MAX_OPTIMIZATION_LEVEL: int = 1


@primitive_dataclass
class SamplerOptions(OptionsV2):
    """Options for v2 Sampler.

    Args:
        optimization_level: How much optimization to perform on the circuits.
            Higher levels generate more optimized circuits,
            at the expense of longer processing times.
            * 0: no optimization
            * 1: light optimization

        dynamical_decoupling: Optional, specify a dynamical decoupling sequence to use.
            Allowed values are ``"XX"``, ``"XpXm"``, ``"XY4"``.
            Default: None

        transpilation: Transpilation options. See :class:`TranspilationOptions` for all
            available options.

        execution: Execution time options. See :class:`ExecutionOptionsV2` for all available options.

        twirling: Pauli-twirling related options. See :class:`TwirlingOptions` for all available options.

        environment: Options related to the execution environment. See
            :class:`EnvironmentOptions` for all available options.

        simulator: Simulator options. See
            :class:`SimulatorOptions` for all available options.

    """

    # Sadly we cannot use pydantic's built in validation because it won't work on Unset.
    optimization_level: Union[UnsetType, int] = Unset
    dynamical_decoupling: Union[UnsetType, DDSequenceType] = Unset
    execution: Union[ExecutionOptionsV2, Dict] = Field(default_factory=ExecutionOptionsV2)
    twirling: Union[TwirlingOptions, Dict] = Field(default_factory=TwirlingOptions)
    experimental: Union[UnsetType, dict] = Unset

    @field_validator("optimization_level")
    @classmethod
    @skip_unset_validation
    def _validate_optimization_level(cls, optimization_level: int) -> int:
        """Validate optimization_leve."""
        if not 0 <= optimization_level <= MAX_OPTIMIZATION_LEVEL:
            raise ValueError(
                "Invalid optimization_level. Valid range is " f"0-{MAX_OPTIMIZATION_LEVEL}"
            )
        return optimization_level
