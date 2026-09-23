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

    from ..options_models.zne import ZneOptions

import numpy as np

from ..exceptions import IBMInputValueError

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
