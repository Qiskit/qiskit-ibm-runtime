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

"""Resilience level default option values."""


def _default_resilience_options(level: int) -> dict:
    """Return default options for resilience level 0"""
    if level == 0:
        return {
            "resilience_level": 0,
            "twirling": {"gates": False, "measure": False},
            "resilience": {
                "measure_noise_mitigation": False,
                "zne_mitigation": False,
                "pec_mitigation": False,
            },
        }

    if level == 1:
        return {
            "resilience_level": 1,
            "twirling": {"gates": True, "measure": True, "strategy": "active-accum"},
            "resilience": {
                "measure_noise_mitigation": True,
                "zne_mitigation": False,
                "pec_mitigation": False,
            },
        }

    if level == 2:
        return {
            "resilience_level": 2,
            "twirling": {"gates": True, "measure": True, "strategy": "active-accum"},
            "resilience": {
                "measure_noise_mitigation": True,
                "zne_mitigation": True,
                "pec_mitigation": False,
                "zne_extrapolator": ("exponential", "linear"),
                "zne_noise_factors": (1, 3, 5),
                "zne_stderr_threshold": 0.25,
            },
        }

    if level == 3:
        return {
            "resilience_level": 3,
            "twirling": {"gates": True, "measure": True, "strategy": "active"},
            "resilience": {
                "measure_noise_mitigation": True,
                "zne_mitigation": False,
                "pec_mitigation": True,
                "pec_max_overhead": 100,
            },
        }
    raise ValueError(f"Invalid resilience level {level}.")
