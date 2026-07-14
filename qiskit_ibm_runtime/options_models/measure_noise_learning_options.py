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

"""Options for measurement noise learning."""

from __future__ import annotations

from typing import Literal

from pydantic.dataclasses import dataclass

from .utils import PRIMITIVES_CONFIG


@dataclass(config=PRIMITIVES_CONFIG)
class MeasureNoiseLearningOptions:
    """Options for measurement noise learning. This is only used by V2 Estimator.

    .. note::
        These options are only used when the resilience level or options specify a
        technique that requires measurement noise learning.
    """

    num_randomizations: int | Literal["auto"] = "auto"
    """The number of random circuits to draw for the measurement learning experiment.

    If "auto", the calibration uses the same number of randomizations
    as specified in the estimator's twirling options.
    """

    shots_per_randomization: int | Literal["auto"] = "auto"
    """The number of shots to use for the learning experiment per random circuit.

    If "auto", the value will be chosen automatically based on the input PUBs.
    """
