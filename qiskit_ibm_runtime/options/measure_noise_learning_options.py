# This code is part of Qiskit.
#
# (C) Copyright IBM 2024-2026.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Options for measurement noise learning."""

from typing import Literal

from pydantic import field_validator

from ..utils.deprecation import issue_deprecation_msg
from .utils import Unset, UnsetType, make_constraint_validator, primitive_dataclass


@primitive_dataclass
class MeasureNoiseLearningOptions:
    """Options for measurement noise learning. This is only used by V2 Estimator.

    .. note::
        These options are only used when the resilience level or options specify a
        technique that requires measurement noise learning.

    """

    num_randomizations: UnsetType | int = Unset
    """The number of random circuits to draw for the measurement learning experiment.

    Default: 32.
    """

    shots_per_randomization: UnsetType | int | Literal["auto"] = Unset
    """The number of shots to use for the learning experiment per random circuit.

    If "auto", the value will be chosen automatically based on the input PUBs.

    Default: "auto".
    """

    _ge1 = make_constraint_validator(
        "num_randomizations",
        "shots_per_randomization",
        ge=1,  # type: ignore[arg-type]
    )

    @field_validator("shots_per_randomization")
    @classmethod
    def _warn_shots_per_randomization_int(
        cls, value: UnsetType | int | Literal["auto"]
    ) -> UnsetType | int | Literal["auto"]:
        """Warn when shots per randomization is set to a deprecated integer value."""
        if isinstance(value, int):
            issue_deprecation_msg(
                msg="Specifying 'measure_noise_learning.shots_per_randomization' as an integer "
                "is deprecated",
                version="0.48.0",
                remedy='Use "auto" instead.',
                stacklevel=3,
            )
        return value
