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

"""Calculate twirling shots for wrapper sampler/estimator."""

import math


def calculate_twirling_shots(
    pub_shots: int,
    num_randomizations: int | str,
    shots_per_randomization: int | str,
) -> tuple[int, int]:
    """Calculate num_randomizations and shots_per_randomization for twirling.

    Implements the logic from TwirlingOptions documentation:

    - If both "auto": shots_per_randomization = max(64, ceil(shots/32))
                     num_randomizations = ceil(shots/shots_per_randomization)
    - If only num_randomizations "auto": num_randomizations = ceil(shots/shots_per_randomization)
    - If only ``shots_per_randomization`` "auto":
      shots_per_randomization = ceil(shots/num_randomizations)

    Args:
        pub_shots: Total shots requested for the pub.
        num_randomizations: Number of randomizations (or "auto").
        shots_per_randomization: Shots per randomization (or "auto").

    Returns:
        Tuple of (num_randomizations, shots_per_randomization).
    """
    if num_randomizations == "auto" and shots_per_randomization == "auto":
        # Both auto: shots_per_rand = max(64, ceil(shots/32))
        shots_per_rand = max(64, math.ceil(pub_shots / 32))
        num_rand = math.ceil(pub_shots / shots_per_rand)
    elif num_randomizations == "auto":
        # Only num_rand auto
        shots_per_rand = int(shots_per_randomization)
        num_rand = math.ceil(pub_shots / shots_per_rand)
    elif shots_per_randomization == "auto":
        # Only shots_per_rand auto
        num_rand = int(num_randomizations)
        shots_per_rand = math.ceil(pub_shots / num_rand)
    else:
        # Both specified
        num_rand = int(num_randomizations)
        shots_per_rand = int(shots_per_randomization)

    return num_rand, shots_per_rand
