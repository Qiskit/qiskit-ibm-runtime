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

"""Translators from EstimatorOptions to qiskit-mitigation inputs."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from ..options_models.twirling import TwirlingOptions
    from ..options_models.zne import ZneOptions


def estimator_options_to_boxing_options(
    twirling_options: TwirlingOptions,
    inject_noise: bool,
    add_tags: bool = False,
) -> dict:
    """Translate twirling options into a ``custom_boxing_options`` dict for qiskit-mitigation.

    This dict is passed directly to ``MitigationTask.prepare()`` (and its subclasses)
    as the ``custom_boxing_options`` argument.

    Noise-injection options (``inject_noise_*``) are intentionally **not** set here for
    PEC and PEA pathways: ``PEC._box_circuit()`` and ``PEA._box_circuit()`` enforce those
    themselves and will raise if we duplicate them with conflicting values.

    ``enable_measures`` and ``measure_annotations`` are also **not** set here. When TREX
    is passed to a task, ``trex._edit_boxing_options()`` forces ``enable_measures=True``
    and ``measure_annotations="all"``. When TREX is absent, ``MitigationTask._box_circuit()``
    defaults to ``measure_annotations="change_basis"``, which is correct.

    For ZNE (gate-folding), ``inject_noise`` is always ``False`` — noise amplification is
    done by circuit folding, not by the boxing pass manager.

    Args:
        twirling_options: The finalized twirling options.
        inject_noise: Whether to request noise-injection annotations in the boxing pass.
            ``True`` only for PEC and PEA; ``False`` for vanilla and ZNE.
        add_tags: Whether to tag boxes with a hash (``True``) or suppress tags (``False``).
            Used in local/simulator mode for noise injection.

    Returns:
        A dict suitable as ``custom_boxing_options`` for qiskit-mitigation task ``prepare()``.
    """
    boxing_opts: dict = {
        # Gate twirling is on when requested OR when noise injection is needed.
        "enable_gates": bool(twirling_options.enable_gates) or inject_noise,
        "twirling_strategy": twirling_options.strategy.replace("-", "_"),
        "twirling_group": twirling_options.group,
        "add_tags": "unique_box" if add_tags else "none",
    }
    # inject_noise_* are only added for PEC/PEA.  PEC/PEA _box_circuit() will
    # also set these, so we must be consistent; for ZNE/vanilla we omit them
    # entirely so the base class defaults apply cleanly.
    if inject_noise:
        boxing_opts["inject_noise_site"] = "after"
        boxing_opts["inject_noise_targets"] = "gates"
        boxing_opts["inject_noise_strategy"] = "uniform_modification"
    return boxing_opts


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


def resolve_zne_noise_factors(
    zne_options: ZneOptions,
) -> tuple[np.ndarray, np.ndarray]:
    """Resolve ``noise_factors`` and ``extrapolated_noise_factors`` from ZneOptions.

    Args:
        zne_options: The finalized ZNE options.

    Returns:
        A tuple ``(noise_factors, extrapolated_noise_factors)`` as float arrays.
    """
    from ..options_models.zne import DEFAULT_NOISE_FACTORS

    noise_factors = (
        np.array(DEFAULT_NOISE_FACTORS, dtype=float)
        if zne_options.noise_factors == "auto"
        else np.array(zne_options.noise_factors, dtype=float)
    )
    extrapolated_noise_factors = (
        np.insert(noise_factors, 0, 0.0).tolist()
        if zne_options.extrapolated_noise_factors == "auto"
        else list(np.array(zne_options.extrapolated_noise_factors, dtype=float))
    )
    return noise_factors, np.array(extrapolated_noise_factors, dtype=float)
