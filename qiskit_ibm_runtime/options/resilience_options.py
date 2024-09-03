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

from typing import Literal, Sequence, Union
from dataclasses import asdict

from pydantic import model_validator, Field

from ..utils.noise_learner_result import LayerError, NoiseLearnerResult
from .utils import Unset, UnsetType, Dict, primitive_dataclass
from .measure_noise_learning_options import MeasureNoiseLearningOptions
from .zne_options import ZneOptions
from .pec_options import PecOptions
from .layer_noise_learning_options import LayerNoiseLearningOptions


NoiseAmplifierType = Literal["LocalFoldingAmplifier",]
ExtrapolatorType = Literal[
    "LinearExtrapolator",
    "QuadraticExtrapolator",
    "CubicExtrapolator",
    "QuarticExtrapolator",
]


@primitive_dataclass
class ResilienceOptionsV2:
    """Resilience options for V2 Estimator.

    Args:
        measure_mitigation: Whether to enable measurement error mitigation method.
            If you enable measurement mitigation, you can fine tune its noise learning
            by using :attr:`~measure_noise_learning`. See :class:`MeasureNoiseLearningOptions`
            for all measurement mitigation noise learning options.
            Default: True.

        measure_noise_learning: Additional measurement noise learning options.
            See :class:`MeasureNoiseLearningOptions` for all options.

        zne_mitigation: Whether to turn on Zero Noise Extrapolation error mitigation method.
            If you enable ZNE, you can fine tune its options by using :attr:`~zne`.
            See :class:`ZneOptions` for additional ZNE related options.
            Default: False.

        zne: Additional zero noise extrapolation mitigation options.
            See :class:`ZneOptions` for all options.

        pec_mitigation: Whether to turn on Probabilistic Error Cancellation error mitigation method.
            If you enable PEC, you can fine tune its options by using :attr:`~pec`.
            See :class:`PecOptions` for additional PEC related options.
            Default: False.

        pec: Additional probabalistic error cancellation mitigation options.
            See :class:`PecOptions` for all options.

        layer_noise_learning: Layer noise learning options.
            See :class:`LayerNoiseLearningOptions` for all options.

        layer_noise_model: A :class:`NoiseLearnerResult` or a sequence of :class:`LayerError`
            objects. If set, all the mitigation strategies that require noise data (e.g., PEC and
            PEA) skip the noise learning stage, and instead gather the required information from
            ``layer_noise_model``. Layers whose information is missing in ``layer_noise_model``
            are treated as noiseless and their noise is not mitigated.
    """

    measure_mitigation: Union[UnsetType, bool] = Unset
    measure_noise_learning: Union[MeasureNoiseLearningOptions, Dict] = Field(
        default_factory=MeasureNoiseLearningOptions
    )
    zne_mitigation: Union[UnsetType, bool] = Unset
    zne: Union[ZneOptions, Dict] = Field(default_factory=ZneOptions)
    pec_mitigation: Union[UnsetType, bool] = Unset
    pec: Union[PecOptions, Dict] = Field(default_factory=PecOptions)
    layer_noise_learning: Union[LayerNoiseLearningOptions, Dict] = Field(
        default_factory=LayerNoiseLearningOptions
    )
    layer_noise_model: Union[UnsetType, NoiseLearnerResult, Sequence[LayerError]] = Unset

    @model_validator(mode="after")
    def _validate_options(self) -> "ResilienceOptionsV2":
        """Validate the model."""
        if not self.measure_mitigation and any(
            value != Unset for value in asdict(self.measure_noise_learning).values()
        ):
            raise ValueError(
                "'measure_noise_learning' options are set, but 'measure_mitigation' is not set to True."
            )

        # Validate not ZNE+PEC
        if self.pec_mitigation is True and self.zne_mitigation is True:
            raise ValueError(
                "pec_mitigation and zne_mitigation`options cannot be "
                "simultaneously enabled. Set one of them to False."
            )

        return self
