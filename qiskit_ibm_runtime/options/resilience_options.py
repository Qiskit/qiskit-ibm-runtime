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

from typing import Sequence, Literal, get_args, Optional, Union
from dataclasses import dataclass, field

from .utils import _flexible
from ..utils.deprecation import issue_deprecation_msg, deprecate_arguments

ResilienceSupportedOptions = Literal[
    "noise_amplifier",
    "noise_factors",
    "extrapolator",
]
NoiseAmplifierType = Literal[
    "TwoQubitAmplifier",
    "GlobalFoldingAmplifier",
    "LocalFoldingAmplifier",
    "CxAmplifier",
]
ExtrapolatorType = Literal[
    "LinearExtrapolator",
    "QuadraticExtrapolator",
    "CubicExtrapolator",
    "QuarticExtrapolator",
]

ZneExtrapolatorType = Literal[
    "multi_exponential",
    "single_exponential",
    "double_exponential",
    "linear",
]


@_flexible
@dataclass
class ResilienceOptions:
    """Resilience options.

    Args:
        noise_factors (DEPRECATED): An list of real valued noise factors that determine
            by what amount the circuits' noise is amplified.
            Only applicable for ``resilience_level=2``.
            Default: (1, 3, 5).

        noise_amplifier (DEPRECATED): A noise amplification strategy. One of ``"TwoQubitAmplifier"``,
            ``"GlobalFoldingAmplifier"``, ``"LocalFoldingAmplifier"``, ``"CxAmplifier"``.
            Only applicable for ``resilience_level=2``.
            Default: "TwoQubitAmplifier".

        extrapolator (DEPRECATED): An extrapolation strategy. One of ``"LinearExtrapolator"``,
            ``"QuadraticExtrapolator"``, ``"CubicExtrapolator"``, ``"QuarticExtrapolator"``.
            Note that ``"CubicExtrapolator"`` and ``"QuarticExtrapolator"`` require more
            noise factors than the default.
            Only applicable for ``resilience_level=2``.
            Default: "LinearExtrapolator".

        trex_mitigation: Whether to enable T-REX error mitigation method.
            By default, T-REX is enabled for resilience level 1, 2, and 3.

        zne_mitigation: Whether to turn on Zero Noise Extrapolation error mitigation method.
            By default, ZNE is enabled for resilience level 2.
        zne_noise_factors: An list of real valued noise factors that determine by what amount the
            circuits' noise is amplified.
            Only applicable if ZNE is enabled.
            Default: (1, 3, 5).
        zne_extrapolator: An extrapolation strategy. One or more of ``"multi_exponential"``,
            ``"single_exponential"``, ``"double_exponential"``, ``"linear"``.
            Only applicable if ZNE is enabled.
            Default: "linear" and "multi_exponential"

        pec_mitigation: Whether to turn on Probabilistic Error Cancellation error mitigation method.
            By default, PEC is enabled for resilience level 3.

    """

    noise_amplifier: NoiseAmplifierType = None
    noise_factors: Sequence[float] = None
    extrapolator: ExtrapolatorType = None

    # TREX
    trex_mitigation: Optional[bool] = None

    # ZNE
    zne_mitigation: Optional[bool] = None
    zne_noise_factors: Sequence[float] = (1, 3, 5)
    zne_extrapolator: Optional[Union[ZneExtrapolatorType, Sequence[ZneExtrapolatorType]]] = field(
        default_factory=lambda: ["linear", "multi_exponential"]
    )

    # PEC
    pec_mitigation: Optional[bool] = None

    @staticmethod
    def validate_resilience_options(resilience_options: dict) -> None:
        """Validate that resilience options are legal.

        Raises:
            ValueError: if any resilience option is not supported
            ValueError: if noise_amplifier is not in NoiseAmplifierType.
            ValueError: if extrapolator is not in ExtrapolatorType.
            ValueError: if extrapolator == "QuarticExtrapolator" and number of noise_factors < 5.
            ValueError: if extrapolator == "CubicExtrapolator" and number of noise_factors < 4.
        """
        if resilience_options.get("noise_amplifier", None) is not None:
            issue_deprecation_msg(
                msg="The 'noise_amplifier' resilience option is deprecated",
                version="0.12.0",
                period="1 month",
                remedy="After the deprecation period, only local folding amplification "
                "will be supported. "
                "Refer to https://github.com/qiskit-community/prototype-zne "
                "for global folding amplification in ZNE.",
            )
        if resilience_options.get("noise_factors", None) is not None:
            deprecate_arguments(
                deprecated="noise_factors",
                version="0.13.0",
                remedy="Please use 'zne_noise_factors' instead.",
            )
        if resilience_options.get("extrapolator", None) is not None:
            deprecate_arguments(
                deprecated="extrapolator",
                version="0.13.0",
                remedy="Please use 'zne_extrapolator' instead.",
            )

        noise_amplifier = resilience_options.get("noise_amplifier")
        if noise_amplifier and noise_amplifier not in get_args(NoiseAmplifierType):
            raise ValueError(
                f"Unsupported value {noise_amplifier} for noise_amplifier. "
                f"Supported values are {get_args(NoiseAmplifierType)}"
            )
        extrapolator = resilience_options.get("extrapolator")
        if extrapolator and extrapolator not in get_args(ExtrapolatorType):
            raise ValueError(
                f"Unsupported value {extrapolator} for extrapolator. "
                f"Supported values are {get_args(ExtrapolatorType)}"
            )
        if (
            extrapolator == "QuarticExtrapolator"
            and len(resilience_options.get("noise_factors")) < 5
        ):
            raise ValueError("QuarticExtrapolator requires at least 5 noise_factors.")
        if extrapolator == "CubicExtrapolator" and len(resilience_options.get("noise_factors")) < 4:
            raise ValueError("CubicExtrapolator requires at least 4 noise_factors.")
