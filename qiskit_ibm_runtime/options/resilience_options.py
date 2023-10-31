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

"""Resilience options."""

from typing import Sequence, Literal, get_args
from pydantic import Field, ConfigDict
from pydantic.functional_validators import model_validator, field_validator
from pydantic.dataclasses import dataclass as pydantic_dataclass

ResilienceSupportedOptions = Literal[
    "noise_amplifier",
    "noise_factors",
    "extrapolator",
]
NoiseAmplifierType = Literal[
    "LocalFoldingAmplifier",
]
ExtrapolatorType = Literal[
    "LinearExtrapolator",
    "QuadraticExtrapolator",
    "CubicExtrapolator",
    "QuarticExtrapolator",
]


@pydantic_dataclass(
    config=ConfigDict(validate_assignment=True, arbitrary_types_allowed=True, extra="forbid")
class ResilienceOptions:
    """Resilience options.

    Args:
        noise_factors: An list of real valued noise factors that determine by what amount the
            circuits' noise is amplified.
            Only applicable for ``resilience_level=2``.
            Default: ``None``, and (1, 3, 5) if resilience level is 2.

        noise_amplifier (DEPRECATED): A noise amplification strategy. Currently only
        ``"LocalFoldingAmplifier"`` is supported Only applicable for ``resilience_level=2``.
            Default: "LocalFoldingAmplifier".

        extrapolator: An extrapolation strategy. One of ``"LinearExtrapolator"``,
            ``"QuadraticExtrapolator"``, ``"CubicExtrapolator"``, ``"QuarticExtrapolator"``.
            Note that ``"CubicExtrapolator"`` and ``"QuarticExtrapolator"`` require more
            noise factors than the default.
            Only applicable for ``resilience_level=2``.
            Default: ``None``, and ``LinearExtrapolator`` if resilience level is 2.
    """

    noise_amplifier: NoiseAmplifierType = None
    noise_factors: Sequence[float] = None
    extrapolator: ExtrapolatorType = None

    @model_validator(mode="after")
    def _validate_model(self):
        noise_amplifier = self.noise_amplifier or "LocalFoldingAmplifier"
        if noise_amplifier not in get_args(NoiseAmplifierType):
            raise ValueError(
                f"Unsupported value {noise_amplifier} for noise_amplifier. "
                f"Supported values are {get_args(NoiseAmplifierType)}"
            )
        extrapolator = self.extrapolator
        if extrapolator and extrapolator not in get_args(ExtrapolatorType):
            raise ValueError(
                f"Unsupported value {extrapolator} for extrapolator. "
                f"Supported values are {get_args(ExtrapolatorType)}"
            )
        if extrapolator == "QuarticExtrapolator" and len(self.noise_factors) < 5:
            raise ValueError("QuarticExtrapolator requires at least 5 noise_factors.")
        if extrapolator == "CubicExtrapolator" and len(self.noise_factors) < 4:
            raise ValueError("CubicExtrapolator requires at least 4 noise_factors.")
        return self
