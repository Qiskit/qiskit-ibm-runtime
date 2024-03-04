# This code is part of Qiskit.
#
# (C) Copyright IBM 2024.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Options for measurement noise learning."""

from typing import Union

from .utils import Unset, UnsetType, primitive_dataclass, make_constraint_validator


@primitive_dataclass
class MeasureNoiseLearningOptions:
    """Options for measurement noise learning.

    .. note::
        These options are only used when the resilience level or options specify a
        technique that requires measurement noise learning.

    Args:
        meas_num_randomizations: The number of random circuits to draw for the measurement
            learning experiment. Default: 32.

        meas_shots_per_randomization: The number of shots to use for the learning experiment
            per random circuit.
    """

    meas_num_randomizations: Union[UnsetType, int] = Unset
    meas_shots_per_randomization: Union[UnsetType, int] = Unset

    _ge1 = make_constraint_validator(
        "meas_num_randomizations", "meas_shots_per_randomization", ge=1
    )
