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

"""Helper functions for the PEC error mitigation method."""

from __future__ import annotations

import math
import sys


def calculate_pec_twirling_shots(
    pub_shots: int,
    num_randomizations: int | str,
    shots_per_randomization: int | str,
) -> tuple[int, int]:
    """Calculate num_randomizations and shots_per_randomization for twirling.

    Implements the logic from TwirlingOptions documentation:

    - If both "auto": shots_per_randomization = 64
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
        shots_per_rand = 64
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


def resolve_pec_max_overhead(
    pec_max_overhead: float | None,
    baseline_num_randomizations: int,
    shots_per_randomization: int,
) -> float:
    """Resolve PEC max_sampling_overhead, applying a safety cap when ``None``.

    When ``max_overhead`` is ``None`` the user requests no limit.  We still need
    to guard against Python integer overflow when gamma is very large, so we cap
    at the largest value that, when multiplied by the total baseline shots, stays
    within ``sys.float_info.max``.

    Args:
        pec_max_overhead: The user-specified maximum overhead, or ``None``.
        baseline_num_randomizations: Baseline number of randomizations (before gamma scaling).
        shots_per_randomization: Shots per randomization.

    Returns:
        A finite ``float`` safe to pass as ``max_sampling_overhead`` to ``PEC.prepare()``.
    """
    if pec_max_overhead is not None:
        return float(pec_max_overhead)
    return sys.float_info.max / (baseline_num_randomizations * shots_per_randomization)
