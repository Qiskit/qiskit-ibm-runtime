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

from typing import Optional, Sequence
from dataclasses import dataclass
from typing_extensions import Literal

from .utils import _flexible

NoiseAmplifierType = Literal[
    "TwoQubitAmplifier",
    "GlobalFoldingAmplifier",
    "LocalFoldingAmplifier",
    "CxAmplifier",
]
ExtrapolatorType = Literal[
    "LinearExtrapolator",
    "PolynomialExtrapolator",
    "QuadraticExtrapolator",
    "CubicExtrapolator",
    "QuarticExtrapolator",
]


@_flexible
@dataclass
class ResilienceOptions:
    """Resilience options.

    Args:
        noise_factors: An list of real valued noise factors that determine by what amount the
            circuits' noise is amplified. Default: (1, 3, 5).

        noise_amplifier: A noise amplification strategy. Default: "TwoQubitAmplifier".

        extrapolator: An extrapolation strategy. Default: "LinearExtrapolator".
    """

    noise_amplifier: NoiseAmplifierType = "TwoQubitAmplifier"
    noise_factors: Sequence[float] = (1, 3, 5)
    extrapolator: ExtrapolatorType = "LinearExtrapolator"
