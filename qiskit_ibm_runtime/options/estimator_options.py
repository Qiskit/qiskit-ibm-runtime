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

"""Estimator options."""

from typing import Union, Literal

from pydantic import Field, field_validator

from .utils import (
    Dict,
    Unset,
    UnsetType,
    skip_unset_validation,
)
from .execution_options import ExecutionOptionsV2
from .resilience_options import ResilienceOptionsV2
from .twirling_options import TwirlingOptions
from .options import OptionsV2
from .utils import primitive_dataclass

DDSequenceType = Literal["XX", "XpXm", "XY4"]
MAX_RESILIENCE_LEVEL: int = 2
MAX_OPTIMIZATION_LEVEL: int = 1


@primitive_dataclass
class EstimatorOptions(OptionsV2):
    """Options for EstimatorV2.

    Args:
        optimization_level: How much optimization to perform on the circuits.
            Higher levels generate more optimized circuits,
            at the expense of longer processing times.
            * 0: no optimization
            * 1: light optimization

        resilience_level: How much resilience to build against errors.
            Higher levels generate more accurate results,
            at the expense of longer processing times.

            * 0: No mitigation.
            * 1: Minimal mitigation costs. Mitigate error associated with readout errors.
            * 2: Medium mitigation costs. Typically reduces bias in estimators but
              is not guaranteed to be zero bias. Only applies to estimator.

            Refer to the
            `Qiskit Runtime documentation
            <https://qiskit.org/documentation/partners/qiskit_ibm_runtime>`_.
            for more information about the error mitigation methods used at each level.

        dynamical_decoupling: Optional, specify a dynamical decoupling sequence to use.
            Allowed values are ``"XX"``, ``"XpXm"``, ``"XY4"``.
            Default: None

        seed_estimator: Seed used to control sampling.

        transpilation: Transpilation options. See :class:`TranspilationOptions` for all
            available options.

        resilience: Advanced resilience options to fine tune the resilience strategy.
            See :class:`ResilienceOptions` for all available options.

        execution: Execution time options. See :class:`ExecutionOptionsV2` for all available options.

        environment: Options related to the execution environment. See
            :class:`EnvironmentOptions` for all available options.

        simulator: Simulator options. See
            :class:`SimulatorOptions` for all available options.

    """

    # Sadly we cannot use pydantic's built in validation because it won't work on Unset.
    optimization_level: Union[UnsetType, int] = Unset
    resilience_level: Union[UnsetType, int] = Unset
    dynamical_decoupling: Union[UnsetType, DDSequenceType] = Unset
    seed_estimator: Union[UnsetType, int] = Unset
    resilience: Union[ResilienceOptionsV2, Dict] = Field(default_factory=ResilienceOptionsV2)
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

    @field_validator("resilience_level")
    @classmethod
    @skip_unset_validation
    def _validate_resilience_level(cls, resilience_level: int) -> int:
        """Validate resilience_level."""
        if not 0 <= resilience_level <= MAX_RESILIENCE_LEVEL:
            raise ValueError(
                "Invalid resilience_level. Valid range is " f"0-{MAX_RESILIENCE_LEVEL}"
            )
        return resilience_level
