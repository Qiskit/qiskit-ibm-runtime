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

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..options_models.twirling import TwirlingOptions


def estimator_options_to_boxing_options(
    twirling_options: TwirlingOptions,
    measure_mitigation: bool,
    inject_noise: bool,
    add_tags: bool = False,
) -> dict:
    """Translate twirling options into a ``custom_boxing_options`` dict for qiskit-mitigation.

    The function assumes that options were finalized and ``twirling_options`` doesn't contain
    ``None``.

    This dict is passed directly to ``MitigationTask.prepare()`` (and its subclasses)
    as the ``custom_boxing_options`` argument.

    Noise-injection options (``inject_noise_*``) are **not** set here — ``PEC``
    and ``PEA`` enforce their own required values for those fields.

    Args:
        twirling_options: The finalized twirling options.
        measure_mitigation: Whether measurement mitigation (TREX) is enabled.
            When ``True``, ``measure_annotations`` is set to ``"all"``; otherwise
            ``"change_basis"``.
        inject_noise: Whether noise-injection boxing is requested (PEC/PEA paths).
            When ``True``, ``enable_gates`` is forced on regardless of the twirling setting.
        add_tags: Whether to tag boxes with a hash (``True``) or suppress tags (``False``).
            Used in local/simulator mode for noise injection.

    Returns:
        A dict suitable as ``custom_boxing_options`` for qiskit-mitigation task ``prepare()``.
    """
    return {
        # Gate twirling is on when requested OR when noise injection is needed.
        "enable_gates": twirling_options.enable_gates or inject_noise,
        "enable_measures": True,
        "twirling_strategy": twirling_options.strategy.replace("-", "_"),
        "twirling_group": twirling_options.group,
        "add_tags": "unique_box" if add_tags else "none",
        "measure_annotations": "all"
        if (measure_mitigation or twirling_options.enable_measure)
        else "change_basis",
    }
