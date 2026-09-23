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

"""Helper functions for client-side Estimator."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

    from qiskit.primitives.containers.estimator_pub import EstimatorPub

    from qiskit_ibm_runtime.options_models.twirling import TwirlingOptions

    from ..options_models.zne import ZneOptions

import numpy as np

from ..exceptions import IBMInputValueError
from ..options_models.zne import DEFAULT_NOISE_FACTORS

_REQUIRED_NOISE_FACTORS = {
    "linear": 2,
    "exponential": 2,
    "double_exponential": 4,
    "fallback": 1,
    **{f"polynomial_degree_{degree}": degree + 1 for degree in range(1, 8)},
}


def resolve_noise_factors(zne_options: ZneOptions) -> tuple[np.ndarray, np.ndarray]:
    """Resolve ``noise_factors`` and ``extrapolated_noise_factors`` into float arrays.

    Args:
        zne_options: The ZNE options to resolve.

    Returns:
        A tuple ``(noise_factors, extrapolated_noise_factors)`` as float arrays.
    """
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


def validate_noise_factors(
    noise_factors: Sequence[float] | np.ndarray, extrapolator: str | Sequence[str]
) -> None:
    """Check that ``noise_factors`` has enough points for every requested extrapolator.

    Args:
        noise_factors: The resolved noise factors that will be used for amplification.
        extrapolator: The extrapolator(s) requested in the ZNE options.

    Raises:
        IBMInputValueError: If ``noise_factors`` is under-specified for any extrapolator.
    """
    extrapolators = [extrapolator] if isinstance(extrapolator, str) else extrapolator
    for extrap in extrapolators:
        required = _REQUIRED_NOISE_FACTORS[extrap]
        if len(noise_factors) < required:
            raise IBMInputValueError(f"{extrap} requires at least {required} noise_factors")


def has_projection_operators(pub: EstimatorPub) -> bool:
    """Return whether an estimator pub contains projection operators in its observables."""
    projection_set = set("01rl+-")
    for observable in pub.observables.ravel():
        for observable_term in observable:
            if bool(set(observable_term) & projection_set):
                return True
    return False


def resolve_precision(
    pubs: list[EstimatorPub],
    run_precision: float | None = None,
) -> float | None:
    """Resolve precision from multiple sources with clear precedence.

    Precedence order (highest to lowest):
    1. Individual pub precision (must be consistent across all pubs)
    2. run() method precision parameter (run_precision)

    Args:
        pubs: List of estimator pubs (may contain precision values).
        run_precision: Precision specified in run() method.

    Returns:
        The resolved precision value, or None if no precision is specified anywhere.

    Raises:
        IBMInputValueError: If pubs have different precision values.
    """
    # Extract precision from pubs
    pub_precisions = {pub.precision if pub.precision is not None else run_precision for pub in pubs}

    if len(pub_precisions) != 1:
        raise IBMInputValueError(
            f"All pubs must have the same precision. Found: {pub_precisions}"
            "(possibly via the run provided precision parameter)"
        )

    if (precision := next(iter(pub_precisions))) is not None and precision <= 0:
        raise IBMInputValueError("The precision value must be strictly greater than 0.")

    return precision


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
