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

from typing import Sequence, Literal, Union, Optional

from pydantic import field_validator, model_validator

from .utils import Unset, UnsetType, skip_unset_validation

# TODO use real base options when available
from ..qiskit.primitives.options import primitive_dataclass


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

ZneExtrapolatorType = Literal[
    "exponential",
    "double_exponential",
    "linear",
    "polynomial_degree_1",
    "polynomial_degree_2",
    "polynomial_degree_3",
    "polynomial_degree_4",
]


@primitive_dataclass
class ResilienceOptionsV2:
    """Resilience options.

    Args:
        measure_noise_mitigation: Whether to enable measurement error mitigation method.
            By default, this is enabled for resilience level 1, 2, and 3 (when applicable).

        zne_mitigation: Whether to turn on Zero Noise Extrapolation error mitigation method.
            By default, ZNE is enabled for resilience level 2.

        zne_noise_factors: An list of real valued noise factors that determine by what amount the
            circuits' noise is amplified.
            Only applicable if ZNE is enabled.

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

        pec_mitigation: Whether to turn on Probabilistic Error Cancellation error mitigation method.
            By default, PEC is enabled for resilience level 3.

        pec_max_overhead: Specify a maximum sampling overhead for the PEC sampling noise model.
            If None the full learned model will be sampled from, otherwise if the learned noise
            model has a sampling overhead greater than this value it will be scaled down to
            implement partial PEC with a scaled noise model corresponding to the maximum
            sampling overhead.
            Only applicable if PEC is enabled.
    """

    # TREX
    measure_noise_mitigation: Union[UnsetType, bool] = Unset
    # TODO: measure_noise_local_model

    # ZNE
    zne_mitigation: Union[UnsetType, bool] = Unset
    zne_noise_factors: Union[UnsetType, Sequence[float]] = Unset
    zne_extrapolator: Union[UnsetType, ZneExtrapolatorType, Sequence[ZneExtrapolatorType]] = Unset
    zne_stderr_threshold: Union[UnsetType, float] = Unset

    # PEC
    pec_mitigation: Union[UnsetType, bool] = Unset
    pec_max_overhead: Union[UnsetType, float] = Unset

    @field_validator("zne_noise_factors")
    @classmethod
    @skip_unset_validation
    def _validate_zne_noise_factors(cls, factors: Sequence[float]) -> Sequence[float]:
        """Validate zne_noise_factors."""
        if any(i < 1 for i in factors):
            raise ValueError("zne_noise_factors` option value must all be >= 1")
        return factors

    @field_validator("zne_stderr_threshold")
    @classmethod
    @skip_unset_validation
    def _validate_zne_stderr_threshold(cls, threshold: float) -> float:
        """Validate zne_stderr_threshold."""
        if threshold <= 0:
            raise ValueError("Invalid zne_stderr_threshold option value must be > 0")
        return threshold

    @field_validator("pec_max_overhead")
    @classmethod
    @skip_unset_validation
    def _validate_pec_max_overhead(cls, overhead: float) -> float:
        """Validate pec_max_overhead."""
        if overhead < 1:
            raise ValueError("pec_max_overhead must be None or >= 1")
        return overhead

    @model_validator(mode="after")
    def _validate_options(self) -> "ResilienceOptionsV2":
        """Validate the model."""
        # Validate ZNE noise factors + extrapolator combination
        if all(
            not isinstance(fld, UnsetType)
            for fld in [self.zne_noise_factors, self.zne_extrapolator]
        ):
            required_factors = {
                "exponential": 2,
                "double_exponential": 4,
                "linear": 2,
                "polynomial_degree_1": 2,
                "polynomial_degree_2": 3,
                "polynomial_degree_3": 4,
                "polynomial_degree_4": 5,
            }
            extrapolators: Sequence = (
                [self.zne_extrapolator]  # type: ignore[assignment]
                if isinstance(self.zne_extrapolator, str)
                else self.zne_extrapolator
            )
            for extrap in extrapolators:
                if len(self.zne_noise_factors) < required_factors[extrap]:  # type: ignore[arg-type]
                    raise ValueError(
                        f"{extrap} requires at least {required_factors[extrap]} zne_noise_factors"
                    )
        # Validate not ZNE+PEC
        if self.pec_mitigation is True and self.zne_mitigation is True:
            raise ValueError(
                "pec_mitigation and zne_mitigation`options cannot be "
                "simultaneously enabled. Set one of them to False."
            )

        return self


# @dataclass(frozen=True)
# class _ZneOptions:
#     zne_mitigation: bool = True
#     zne_noise_factors: Sequence[float] = (1, 3, 5)
#     zne_extrapolator: Union[ZneExtrapolatorType, Sequence[ZneExtrapolatorType]] = (
#         "exponential",
#         "linear",
#     )
#     zne_stderr_threshold: float = 0.25


# @dataclass(frozen=True)
# class _PecOptions:
#     pec_mitigation: bool = True
#     pec_max_overhead: float = 100


@primitive_dataclass
class ResilienceOptionsV1:
    """Resilience options.

    Args:
        noise_factors: An list of real valued noise factors that determine by what amount the
            circuits' noise is amplified.
            Only applicable for ``resilience_level=2``.
            Default: ``None``, and (1, 3, 5) if resilience level is 2.

        noise_amplifier: A noise amplification strategy. Currently only
        ``"LocalFoldingAmplifier"`` is supported Only applicable for ``resilience_level=2``.
            Default: "LocalFoldingAmplifier".

        extrapolator: An extrapolation strategy. One of ``"LinearExtrapolator"``,
            ``"QuadraticExtrapolator"``, ``"CubicExtrapolator"``, ``"QuarticExtrapolator"``.
            Note that ``"CubicExtrapolator"`` and ``"QuarticExtrapolator"`` require more
            noise factors than the default.
            Only applicable for ``resilience_level=2``.
            Default: ``None``, and ``LinearExtrapolator`` if resilience level is 2.
    """

    noise_amplifier: Optional[NoiseAmplifierType] = None
    noise_factors: Optional[Sequence[float]] = None
    extrapolator: Optional[ExtrapolatorType] = None

    @model_validator(mode="after")
    def _validate_options(self) -> "ResilienceOptionsV1":
        """Validate the model."""
        required_factors = {
            "QuarticExtrapolator": 5,
            "CubicExtrapolator": 4,
        }
        req_len = required_factors.get(self.extrapolator, None)
        if req_len and len(self.noise_factors) < req_len:
            raise ValueError(f"{self.extrapolator} requires at least {req_len} noise_factors.")

        return self
