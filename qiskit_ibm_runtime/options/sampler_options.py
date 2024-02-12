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

from pydantic import Field

from .utils import (
    Dict,
    Unset,
    UnsetType,
)
from .execution_options import ExecutionOptionsV2
from .transpilation_options import TranspilationOptionsV2
from .twirling_options import TwirlingOptions
from .options import OptionsV2
from .utils import primitive_dataclass

DDSequenceType = Literal["XX", "XpXm", "XY4"]


@primitive_dataclass
class SamplerOptions(OptionsV2):
    """Options for v2 Sampler.

    Args:
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
    dynamical_decoupling: Union[UnsetType, DDSequenceType] = Unset
    transpilation: Union[TranspilationOptionsV2, Dict] = Field(
        default_factory=TranspilationOptionsV2
    )
    execution: Union[ExecutionOptionsV2, Dict] = Field(default_factory=ExecutionOptionsV2)
    twirling: Union[TwirlingOptions, Dict] = Field(default_factory=TwirlingOptions)
    experimental: Union[UnsetType, dict] = Unset
