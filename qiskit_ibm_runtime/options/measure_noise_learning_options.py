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

    shots_per_randomization: UnsetType | Literal["auto"] = Unset
    """The number of shots to use for the learning experiment per random circuit.

    If "auto", the value will be chosen automatically based on the input PUBs.

    Default: "auto".
    """

    _ge1 = make_constraint_validator(
        "num_randomizations",
        ge=1,  # type: ignore[arg-type]
    )

    @field_validator("shots_per_randomization")
    @classmethod
    def _warn_shots_per_randomization_set(
        cls, value: UnsetType | Literal["auto"]
    ) -> UnsetType | Literal["auto"]:
        """Warn when shots per randomization is set, as the field is being removed."""
        if not isinstance(value, UnsetType):
            issue_deprecation_msg(
                msg="The 'measure_noise_learning.shots_per_randomization' option is deprecated "
                "and will be removed soon",
                version="0.51.0",
                remedy="Do not set this option.",
                stacklevel=3,
            )
        return value
