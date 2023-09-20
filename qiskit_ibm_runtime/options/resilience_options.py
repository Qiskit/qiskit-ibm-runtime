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

from typing import Sequence, Literal, get_args, Union
from dataclasses import dataclass

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
    None,
    "exponential",
    "double_exponential",
    "linear",
    "polynomial_degree_1",
    "polynomial_degree_2",
    "polynomial_degree_3",
    "polynomial_degree_4",
]


@_flexible
@dataclass
class ResilienceOptions:
    """Resilience options.

    Args:
        noise_factors (DEPRECATED): An list of real valued noise factors that determine
            by what amount the circuits' noise is amplified.
            Only applicable for ``resilience_level=2``.
            Default: (1, 3, 5) if resilience level is 2. Otherwise ``None``.

        noise_amplifier (DEPRECATED): A noise amplification strategy. One of ``"TwoQubitAmplifier"``,
            ``"GlobalFoldingAmplifier"``, ``"LocalFoldingAmplifier"``, ``"CxAmplifier"``.
            Only applicable for ``resilience_level=2``.
            Default: "TwoQubitAmplifier" if resilience level is 2. Otherwise ``None``.

        extrapolator (DEPRECATED): An extrapolation strategy. One of ``"LinearExtrapolator"``,
            ``"QuadraticExtrapolator"``, ``"CubicExtrapolator"``, ``"QuarticExtrapolator"``.
            Note that ``"CubicExtrapolator"`` and ``"QuarticExtrapolator"`` require more
            noise factors than the default.
            Only applicable for ``resilience_level=2``.
            Default: ``LinearExtrapolator`` if resilience level is 2. Otherwise ``None``.

        measure_noise_mitigation: Whether to enable measurement error mitigation method.
            By default, this is enabled for resilience level 1, 2, and 3 (when applicable).

        zne_mitigation: Whether to turn on Zero Noise Extrapolation error mitigation method.
            By default, ZNE is enabled for resilience level 2.

        zne_noise_factors: An list of real valued noise factors that determine by what amount the
            circuits' noise is amplified.
            Only applicable if ZNE is enabled.
            Default: (1, 3, 5).

        zne_extrapolator: An extrapolation strategy. One or more of ``"multi_exponential"``,
            ``"single_exponential"``, ``"double_exponential"``, ``"linear"``.
            Only applicable if ZNE is enabled.
            Default: ``("exponential, "linear")``

        zne_stderr_threshold: A standard error threshold for accepting the ZNE result of Pauli basis
            expectation values when using ZNE mitigation. Any extrapolator model resulting an larger
            standard error than this value, or mean that is outside of the allowed range and threshold
            will be rejected. If all models are rejected the result for the lowest noise factor is
            used for that basis term.
            Only applicable if ZNE is enabled.
            Default: 0.25

        pec_mitigation: Whether to turn on Probabilistic Error Cancellation error mitigation method.
            By default, PEC is enabled for resilience level 3.

        pec_max_overhead: Specify a maximum sampling overhead for the PEC sampling noise model.
            If None the full learned model will be sampled from, otherwise if the learned noise
            model has a sampling overhead greater than this value it will be scaled down to
            implement partial PEC with a scaled noise model corresponding to the maximum
            sampling overhead.
            Only applicable if PEC is enabled.
            Default: 100
    """

    noise_amplifier: NoiseAmplifierType = None
    noise_factors: Sequence[float] = None
    extrapolator: ExtrapolatorType = None

    # Measurement error mitigation
    measure_noise_mitigation: bool = None

    # ZNE
    zne_mitigation: bool = None
    zne_noise_factors: Sequence[float] = None
    zne_extrapolator: Union[ZneExtrapolatorType, Sequence[ZneExtrapolatorType]] = ("exponential", "linear")
    zne_stderr_threshold: float = None

    # PEC
    pec_mitigation: bool = None
    pec_max_overhead: float = None

    @staticmethod
    def validate_resilience_options(resilience_options: dict) -> None:
        """Validate that resilience options are legal.

        Raises:
            ValueError: if any resilience option is not supported
            ValueError: if noise_amplifier is not in NoiseAmplifierType.
            ValueError: if extrapolator is not in ExtrapolatorType.
            ValueError: if extrapolator == "QuarticExtrapolator" and number of noise_factors < 5.
            ValueError: if extrapolator == "CubicExtrapolator" and number of noise_factors < 4.
            TypeError: if an input value has an invalid type.
        """
        noise_amplifier = resilience_options.get("noise_amplifier")
        if noise_amplifier is not None:
            issue_deprecation_msg(
                msg="The 'noise_amplifier' resilience option is deprecated",
                version="0.12.0",
                period="1 month",
                remedy="After the deprecation period, only local folding amplification "
                "will be supported. "
                "Refer to https://github.com/qiskit-community/prototype-zne "
                "for global folding amplification in ZNE.",
            )
            if noise_amplifier not in get_args(NoiseAmplifierType):
                raise ValueError(
                    f"Unsupported value {noise_amplifier} for noise_amplifier. "
                    f"Supported values are {get_args(NoiseAmplifierType)}"
                )

        if resilience_options.get("noise_factors", None) is not None:
            deprecate_arguments(
                deprecated="noise_factors",
                version="0.13.0",
                remedy="Please use 'zne_noise_factors' instead.",
            )

        extrapolator = resilience_options.get("extrapolator")
        if extrapolator is not None:
            deprecate_arguments(
                deprecated="extrapolator",
                version="0.13.0",
                remedy="Please use 'zne_extrapolator' instead.",
            )
            if extrapolator not in get_args(ExtrapolatorType):
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

        # Validation of new ZNE options
        if resilience_options.get("zne_mitigation"):
            # Validate extrapolator
            extrapolator = resilience_options.get("zne_extrapolator")
            if isinstance(extrapolator, str):
                extrapolator = (extrapolator,)
            if extrapolator is not None:
                for extrap in extrapolator:
                    if extrap not in get_args(ZneExtrapolatorType):
                        raise ValueError(
                            f"Unsupported value {extrapolator} for zne_extrapolator. "
                            f"Supported values are {get_args(ZneExtrapolatorType)}"
                        )

            # Validation of noise factors
            factors = resilience_options.get("zne_noise_factors")
            if not isinstance(factors, (list, tuple)):
                raise TypeError(
                    f"zne_noise_factors option value must be a sequence, not {type(factors)}"
                )
            if any(i <= 0 for i in factors):
                raise ValueError("zne_noise_factors` option value must all be non-negative")
            if len(factors) < 1:
                raise ValueError("zne_noise_factors cannot be empty")
            if extrapolator is not None:
                required_factors = {
                    "exponential": 2,
                    "double_exponential": 4,
                    "linear": 2,
                    "polynomial_degree_1": 2,
                    "polynomial_degree_2": 3,
                    "polynomial_degree_3": 4,
                    "polynomial_degree_4": 5,
                }
                for extrap in extrapolator:
                    if len(factors) < required_factors[extrap]:
                        raise ValueError(
                            f"{extrap} requires at least {required_factors[extrap]} zne_noise_factors"
                        )

            # Validation of threshold
            threshold = resilience_options.get("zne_stderr_threshold")
            if threshold is not None and threshold <= 0:
                raise ValueError("Invalid zne_stderr_threshold option value must be > 0")

        if resilience_options.get("pec_mitigation"):
            if resilience_options.get("zne_mitigation"):
                raise ValueError(
                    "pec_mitigation and zne_mitigation`options cannot be "
                    "simultaneously enabled. Set one of them to False."
                )
            max_overhead = resilience_options.get("pec_max_overhead")
            if max_overhead is not None and max_overhead < 1:
                raise ValueError("pec_max_overhead must be None or >= 1")


@dataclass(frozen=True)
class _ZneOptions:
    zne_mitigation: bool = True
    zne_noise_factors: Sequence[float] = (1, 3, 5)
    zne_extrapolator: Union[ZneExtrapolatorType, Sequence[ZneExtrapolatorType]] = (
        "exponential",
        "linear",
    )
    zne_stderr_threshold: float = 0.25


@dataclass(frozen=True)
class _PecOptions:
    pec_mitigation: bool = True
    pec_max_overhead: float = 100
