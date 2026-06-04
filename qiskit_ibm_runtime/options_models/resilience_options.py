# This code is part of Qiskit.
#
# (C) Copyright IBM 2026.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Resilience options."""

from __future__ import annotations

from pydantic import Field
from pydantic.dataclasses import dataclass

from .measure_noise_learning_options import MeasureNoiseLearningOptions
from .utils import PRIMITIVES_CONFIG


@dataclass(config=PRIMITIVES_CONFIG)
class ResilienceOptions:
    """Resilience options for V2 Estimator."""

    measure_mitigation: bool = True
    """Whether to enable measurement error mitigation method.

    If you enable measurement mitigation, you can fine-tune its noise learning
    by using :attr:`~measure_noise_learning`. See :class:`MeasureNoiseLearningOptions`
    for all measurement mitigation noise learning options.
    """
    measure_noise_learning: MeasureNoiseLearningOptions = Field(
        default_factory=MeasureNoiseLearningOptions
    )

    """Additional measurement noise learning options.

    See :class:`MeasureNoiseLearningOptions` for all options.
    """
