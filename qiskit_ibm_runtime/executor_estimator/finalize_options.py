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

"""Utility for finalizing EstimatorOptions."""

from __future__ import annotations

import warnings
from copy import deepcopy
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..options_models.estimator import EstimatorOptions

# Default configuration for resilience levels used to finalize estimator options.
_RESILIENCE_LEVEL_DEFAULTS = {
    0: {
        "enable_gates": False,
        "enable_measure": False,
        "measure_mitigation": False,
        "zne_mitigation": False,
    },
    1: {
        "enable_gates": False,
        "enable_measure": True,
        "measure_mitigation": True,
        "zne_mitigation": False,
    },
    2: {
        "enable_gates": True,
        "enable_measure": True,
        "measure_mitigation": True,
        "zne_mitigation": True,
    },
}


def _force_twirling_field(
    field: str,
    twirling_options: Any,
    user_twirling_fields: set[str],
    mitigation: str,
) -> None:
    """Force a twirling field to ``True``, warning if the user had explicitly set it ``False``."""
    if field in user_twirling_fields and getattr(twirling_options, field) is False:
        warnings.warn(
            f"twirling.{field}=False was explicitly set, but {mitigation} requires "
            f"twirling.{field}=True. The value is being overridden to True.",
            UserWarning,
            stacklevel=4,
        )
    setattr(twirling_options, field, True)


def finalize_estimator_options(options: EstimatorOptions) -> EstimatorOptions:
    """Return a finalized copy of *options*.

    Applies resilience-level defaults for any fields left as ``None``, then enforces
    required option dependencies (e.g. measurement mitigation forces measurement twirling).

    Args:
        options: The un-finalized :class:`~.EstimatorOptions` to process.

    Returns:
        A finalized copy of the given :class:`~.EstimatorOptions`.
    """
    finalized_options = deepcopy(options)
    defaults = _RESILIENCE_LEVEL_DEFAULTS[finalized_options.resilience_level]

    if finalized_options.twirling.enable_gates is None:
        finalized_options.twirling.enable_gates = defaults["enable_gates"]
    if finalized_options.twirling.enable_measure is None:
        finalized_options.twirling.enable_measure = defaults["enable_measure"]
    if finalized_options.resilience.measure_mitigation is None:
        finalized_options.resilience.measure_mitigation = defaults["measure_mitigation"]
    if finalized_options.resilience.zne_mitigation is None:
        finalized_options.resilience.zne_mitigation = defaults["zne_mitigation"]

    user_twirling_fields = options.twirling.model_fields_set

    if finalized_options.resilience.measure_mitigation is True:
        _force_twirling_field(
            "enable_measure",
            finalized_options.twirling,
            user_twirling_fields,
            "measurement mitigation",
        )

    if (
        finalized_options.resilience.zne_mitigation is True
        and finalized_options.resilience.zne.amplifier == "pea"
    ):
        _force_twirling_field(
            "enable_gates",
            finalized_options.twirling,
            user_twirling_fields,
            "PEA mitigation",
        )
        _force_twirling_field(
            "enable_measure",
            finalized_options.twirling,
            user_twirling_fields,
            "PEA mitigation",
        )

    if finalized_options.resilience.pec_mitigation is True:
        _force_twirling_field(
            "enable_gates",
            finalized_options.twirling,
            user_twirling_fields,
            "PEC mitigation",
        )
        _force_twirling_field(
            "enable_measure",
            finalized_options.twirling,
            user_twirling_fields,
            "PEC mitigation",
        )

    return finalized_options
