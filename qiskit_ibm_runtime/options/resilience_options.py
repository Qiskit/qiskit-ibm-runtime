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
    None,
    "exponential",
    "double_exponential",
    "linear",
    "polynomial_degree_1",
    "polynomial_degree_2",
    "polynomial_degree_3",
    "polynomial_degree_4",
]


@dataclass
class ResilienceOptions:
    """Resilience options.

    Args:
        noise_factors (DEPRECATED): An list of real valued noise factors that determine
            by what amount the circuits' noise is amplified.
            Only applicable for ``resilience_level=2``.
            Default: (1, 3, 5) if resilience level is 2. Otherwise ``None``.

        noise_amplifier (DEPRECATED): A noise amplification strategy. Currently only
        ``"LocalFoldingAmplifier"`` is supported Only applicable for ``resilience_level=2``.
            Default: "LocalFoldingAmplifier".

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

        zne_amplifier: The method to use when amplifying noise to the intended noise factors.
            Default: `"gate_folding"`.

        zne_stderr_threshold: A standard error threshold for accepting the ZNE result of Pauli basis
            expectation values when using ZNE mitigation. Any extrapolator model resulting an larger
            standard error than this value, or mean that is outside of the allowed range and threshold
            will be rejected. If all models are rejected the result for the lowest noise factor is
            used for that basis term.
            Only applicable if ZNE is enabled.
            Default: 0.25

        zne_return_all_extrapolated: If True return an array of the extrapolated expectation values
            for all input ``zne_extrapolator`` models, along with the automatically selected
            extrapolated value. If False only return the automatically selected extrapolated value.
            Default: False

        zne_return_unextrapolated: If True return the unextrapolated expectation values for each
            of ihe input ``zne_noise_factors`` along with the extrapolated values as an array
            valued result. If False only return the extrapolated values.
            Default: False

        zne_extrapolated_noise_factors: Specify 1 or more noise factor values to evaluate the
            extrapolated models at. If a sequence of values the returned results will be array
            valued with specified noise factor evaluated for the extrapolation model. A value
            of 0 corresponds to zero-noise extrapolation.
            Default: 0

        pec_mitigation: Whether to turn on Probabilistic Error Cancellation error mitigation method.
            By default, PEC is enabled for resilience level 3.

        pec_max_overhead: Specify a maximum sampling overhead for the PEC sampling noise model.
            If None the full learned model will be sampled from, otherwise if the learned noise
            model has a sampling overhead greater than this value it will be scaled down to
            implement partial PEC with a scaled noise model corresponding to the maximum
            sampling overhead.
            Only applicable if PEC is enabled.
            Default: 100

        measure_noise_learning_shots: Specify a custom number of total shots to run for learning
            the Pauli twirled measure noise when applying measure noise mitigation. If `"auto"`
            the number of shots will be determined based on the execution options.
            Default: ``"auto"``

        measure_noise_learning_samples: Specify the number of twirling samples to run when
            learning the Pauli twirled measure noise model.
            Default: 32

        layer_noise_learning_max_experiments: Specify the maximum number of layer noise learning
            experiments that can be run when characterization layer noise for PEC.
            Default: 3

        layer_noise_learning_shots: Specify the total number of shots to run for each Pauli
            twirled measurement circuit to run when learning the layer noise of an
            individual layer for PEC.
            Default: 4096

        layer_noise_learning_samples: Specify the number of twirling samples to run per
            measurement circuit when learning the layer noise of an individual layer for
            PEC.
            Default: 32.

        layer_noise_learning_depths: Specify a custom sequence of layer pair depths to use when
            running learning experiments for layer noise for PEC. If None a default
            value will be used.
            Default: None
    """

    noise_amplifier: NoiseAmplifierType = None
    noise_factors: Sequence[float] = None
    extrapolator: ExtrapolatorType = None

    # Measurement error mitigation
    measure_noise_mitigation: bool = None

    # ZNE
    zne_mitigation: bool = None
    zne_noise_factors: Sequence[float] = None
    zne_extrapolator: Union[ZneExtrapolatorType, Sequence[ZneExtrapolatorType]] = (
        "exponential",
        "linear",
    )
    zne_amplifier: str = "gate_folding"
    zne_stderr_threshold: float = None
    zne_return_all_extrapolated: bool = False
    zne_return_unextrapolated: bool = False
    zne_extrapolated_noise_factors: Union[float, Sequence[float]] = 0

    # PEC
    pec_mitigation: bool = None
    pec_max_overhead: float = None

    # Measure noise learning options
    measure_noise_learning_shots: Union[int, Literal["auto"]] = "auto"
    measure_noise_learning_samples: int = 32

    # Layer noise learning options
    layer_noise_learning_max_experiments: int = 3
    layer_noise_learning_shots: int = 32 * 128
    layer_noise_learning_samples: int = 32
    layer_noise_learning_depths: Sequence[int] = None

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
        noise_amplifier = resilience_options.get("noise_amplifier") or "LocalFoldingAmplifier"
        if noise_amplifier not in get_args(NoiseAmplifierType):
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
