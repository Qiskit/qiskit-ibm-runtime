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

"""Extrapolation functions used for zero noise extrapolation (ZNE)."""

from __future__ import annotations

import re
import warnings
from typing import TYPE_CHECKING

import numpy as np
from numpy.polynomial.polynomial import polyval
from scipy.optimize import curve_fit

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    import numpy.typing as npt


_VALID_NAMES = [
    "linear",
    "exponential",
    "double_exponential",
    "polynomial_degree_(1 <= k <= 7)",
    "fallback",
]

_NON_POLYNOMIAL_MODELS = frozenset({"fallback", "exponential", "double_exponential"})


def process_extrapolated_expectation_values(
    noise_scaled_exp_vals: npt.ArrayLike,
    noise_scaled_standard_errors: npt.ArrayLike,
    observable_term: str,
    zne_noise_factors: Sequence[float],
    extrapolators: str | Sequence[str],
    extrapolated_noise_factors: float | int | npt.ArrayLike = 0,
) -> tuple[npt.NDArray[float], npt.NDArray[float], npt.NDArray[str]]:
    r"""Calculate extrapolated expectation values based on noise-amplified expectation values.

    The requested model(s) are fit to the expectation values measured at the noise factors for
    the single given observable term and evaluated at the target noise factor(s) (``0`` for zero
    noise). Models are tried in priority order: each target noise factor takes the result of the
    first model with a valid extrapolation. An extrapolation is valid when its value and standard
    error are finite, the standard error is within the basis threshold, and
    :math:`value \pm stderr` lies within the observable's ideal range widened by that threshold.
    The range varies based on the observable term: ``[0, 1]`` for projector-only observable terms,
    ``[-1, 1]`` for observable terms containing Paulis, and unbounded when the observable term is
    absent or unrecognized. If no model produces a valid extrapolation, the candidate with the
    smallest standard error is used (non-finite errors are treated as infinite). Include
    ``fallback`` in ``extrapolator`` to add the lowest-noise measured value as a candidate, so it
    is selected when the fitted models fail.

    The standard errors reported for the extrapolated values are first-order estimates
    propagated from the fit covariance. For details see the confidence and prediction intervals
    section of this kapteyn tutorial, `link
    <https://www.astro.rug.nl/software/kapteyn/kmpfittutorial.html#confidence-and-prediction-intervals>`_.

    Args:
        noise_scaled_exp_vals: Noise amplified expectation value result for a single observable
            term. The scaled exp vals is a 1D array with the same length as ``zne_noise_factors``.
        noise_scaled_standard_errors: Standard deviations of the Noise amplified results. Have the
            same shape as ``noise_scaled_exp_vals``.
        observable_term: The observable term to calculate expectation values for. The observable
            term determine the ideal-value range used to judge extrapolation validity.
        zne_noise_factors: The noise factors used to amplify the noise.
        extrapolators: A builtin model name, or a sequence of names tried in priority order.
            Supported (each fits the named function of the noise factor ``x``):

            - ``linear``: ``a + b*x``
            - ``polynomial_degree_k`` (1 <= k <= 7): a degree-k polynomial
            - ``exponential``: ``a*exp(b*x)``
            - ``double_exponential``: ``a*exp(b*x) + c*exp(d*x)`` (rates constrained to decay)
            - ``fallback``: no fit; the measured value at the lowest noise factor
        extrapolated_noise_factors: Scalar or 1D array of noise factors to evaluate the fits
            at; defaults to ``0`` (zero-noise extrapolation).

    Raises:
        ValueError: If an extrapolator name is not recognized.

    Returns:
        A tuple ``(exp_vals, stds, extrapolators)``, where ``exp_vals`` are
        expectation values evaluated at ``extrapolated_noise_factors``, ``stds`` are
        standard deviations. ``extrapolators`` are the valid extrapolation methods selected.
    """
    if isinstance(extrapolators, str):
        extrapolators = [extrapolators]

    if isinstance(extrapolated_noise_factors, (float, int)):
        extrapolated_noise_factors = [extrapolated_noise_factors]

    if {
        len(noise_scaled_exp_vals),
        len(noise_scaled_standard_errors),
    } != {len(zne_noise_factors)}:
        raise ValueError(
            f"Number of expectation value items ({len(noise_scaled_exp_vals)}), "
            f" and standard deviation items ({len(noise_scaled_standard_errors)}) "
            f" must be equal to the number noise factors ({len(zne_noise_factors)})."
        )

    extrapolated_values, extrapolated_stderr = fit_extrapolation_models(
        noise_scaled_exp_vals,
        noise_scaled_standard_errors,
        zne_noise_factors,
        models=extrapolators,
        extrapolated_noise_factor=extrapolated_noise_factors,
    )

    # choose the best extrapolated result
    return select_zne_extrapolated_result(
        extrapolated_values,
        extrapolated_stderr,
        observable_term,
        extrapolators,
    )


def fit_extrapolation_models(
    values: Sequence[float],
    standard_error: Sequence[float],
    zne_noise_factors: Sequence[float],
    models: Sequence[str],
    extrapolated_noise_factor: float | npt.ArrayLike = 0,
) -> tuple[npt.NDArray[float], npt.NDArray[float]]:
    """Fit each model to the noise-scaled data and evaluate at the extrapolation points.

    Args:
        values: Expectation values used for the extrapolation.
        standard_error: Standard errors of the expectation values.
        zne_noise_factors: Amplification factors used for fitting the noise.
        models: Models to use for fitting.
        extrapolated_noise_factor: Points to extrapolate to.

    Returns:
        A tuple ``(fit_values, fit_stderrs)`` where ``fit_values`` and ``fit_stderrs``
        are 2D arrays whose first axis indexes the model and second axis the extrapolated
        noise factor.
    """
    y_data = np.asarray(values, dtype=float)
    y_std = np.asarray(standard_error, dtype=float)
    x_data = np.asarray(zne_noise_factors, dtype=float)

    # Make noise factor(s) arrays
    x_eval = as_noise_factors(extrapolated_noise_factor)

    # Clamp negative/0.0 stds to min(y_std). Clamp inf/NaN stds to max(y_std).
    # If no valid stds, function returns None
    fit_stds = clamp_degenerate_stds(y_std)

    # Ensure the extrapolators are valid
    names = list(models)
    for name in names:
        if name not in _NON_POLYNOMIAL_MODELS and poly_degree(name) is None:
            raise ValueError(
                f"Unsupported extrapolator name: {name}, must be one of {_VALID_NAMES}"
            )

    # Extrapolate to the lowest noise scale's values when the extrapolator is "fallback"
    fallback_idx = int(np.argmin(x_data))

    # Get arrays of extrapolated EVs and associated standard errors.
    # Arrays are shaped (# extrapolators, # extrapolated noise factors).
    fit_values = np.empty((len(names), x_eval.size))
    fit_stderrs = np.empty_like(fit_values)
    for i, name in enumerate(names):
        fit_values[i], fit_stderrs[i] = extrapolate(
            name, x_data, y_data, y_std, fit_stds, x_eval, fallback_idx
        )

    return fit_values, fit_stderrs


def clamp_degenerate_stds(y_std: np.ndarray) -> np.ndarray | None:
    """Per-point standard errors for fitting, with degenerate errors clamped.

    Standard errors of ``0`` or negative are clamped up to the smallest finite error
    and ``inf``/``nan`` down to the largest, keeping every value finite and positive.
    If no standard error is positive and finite, returns ``None`` so the caller
    performs an unweighted fit.
    """
    finite = y_std[(y_std > 0) & (y_std < np.inf)]
    if not np.any(finite):
        warnings.warn(
            "No positive, finite standard errors were found; falling back to an "
            "unweighted fit for extrapolation.",
            stacklevel=2,
        )
        return None
    # Map nan to inf so it clamps to the largest error rather than propagating nan.
    return np.clip(np.nan_to_num(y_std, nan=np.inf), finite.min(), finite.max())


def select_zne_extrapolated_result(
    zne_values: npt.NDArray[float],
    zne_std_errors: npt.NDArray[float],
    observable_term: str,
    zne_extrapolator: Sequence[str],
) -> tuple[npt.NDArray[float], npt.NDArray[float], npt.NDArray[str]]:
    """Choose the best extrapolated values.

    The best value is the valid value produced by the highest-priority model. Valid values are
    those that are finite, have a standard error within the measurement-basis threshold, and lie
    within the basis's range to within that standard error.

    Args:
        zne_values: Extrapolated expectation values.
        zne_std_errors: Standard errors of the extrapolated expectation values.
        observable_term: The observable term to calculate expectation values for. The observable
            determine the ideal-value range used to judge extrapolation validity.
        zne_extrapolator: The extrapolators used.

    Returns:
        A tuple ``(accept_values, accept_stderrs, accept_extrap)`` of the chosen best expectation
        values, and the associated standard errors and extrapolator.
    """
    # Patterns for matching ev bases for range of ideal outcomes.
    # Range [0, 1] for basis containing only I and projectors.
    # Range [-1, 1] for bases containing non-I Paulis.
    _pattern_ylim_01 = re.compile(r"^[I01lr+\-]+$")
    _pattern_ylim_pm1 = re.compile(r"^[XYZI01lr+\-]+$")

    # Determine ideal value limits for standard basis projectors. If there is any
    # Pauli in the basis term we assume ideal <B> in [-1, 1], for only projectors [0, 1].
    # For missing or non-standard basis don't constrain values
    if re.search(_pattern_ylim_01, observable_term):
        val_min, val_max = (0, 1)
    elif re.search(_pattern_ylim_pm1, observable_term):
        val_min, val_max = (-1, 1)
    else:
        val_min, val_max = (-np.inf, np.inf)

    # Filter candidate values that have non-finite values/std errors and values
    # with standard errors outside the basis threshold.
    stderr_threshold = max(abs(val_min), abs(val_max))
    reject_conditions = np.stack(
        [
            np.logical_not(np.isfinite(zne_values)),
            np.logical_not(np.isfinite(zne_std_errors)),
            zne_std_errors > stderr_threshold,
            zne_values - zne_std_errors < val_min - stderr_threshold,
            zne_values + zne_std_errors > val_max + stderr_threshold,
        ],
        axis=-1,
    )
    accept = np.logical_not(np.any(reject_conditions, axis=-1))

    # Fallback index is the lowest stderror result if none satisfy acceptance
    # criteria. Here we map NaN to Inf since argmin treats NaN < 0.
    fallback_indices = np.argmin(np.nan_to_num(zne_std_errors, nan=np.inf), axis=0)

    # Iterate across each extrapolated noise scale and select the output from the
    # highest-priority (lowest indexed) model that produced a valid output.
    # If no model gives a valid output for a noise scale, the value with the lowest
    # stderr will be chosen.
    accept_values = np.zeros(zne_values.shape[1:], dtype=float)
    accept_stderrs = np.zeros_like(accept_values)
    accept_extrap = np.zeros_like(accept_values, dtype=object)
    for idx, col in enumerate(accept.T):
        accepted = np.where(col)[0]
        accepted_idx = accepted[0] if accepted.size else fallback_indices[idx]
        fits_idx = (accepted_idx, idx)
        accept_values[idx] = zne_values[fits_idx]
        accept_stderrs[idx] = zne_std_errors[fits_idx]
        accept_extrap[idx] = zne_extrapolator[accepted_idx]

    return accept_values, accept_stderrs, accept_extrap


def extrapolate(
    name: str,
    x: np.ndarray,
    y: np.ndarray,
    y_std: np.ndarray,
    fit_stds: np.ndarray | None,
    x_eval: np.ndarray,
    fallback_idx: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Extrapolated values and stderrs for one model; NaN-filled on fit failure."""
    # No extrapolation. Fall back to a pre-defined set of data.
    if name == "fallback":
        return (
            np.full(x_eval.shape, y[fallback_idx]),
            np.full(x_eval.shape, y_std[fallback_idx]),
        )
    try:
        # Get a SciPy model specification. p0 is required for curve_fit to infer
        # the number of parameters over which to optimize. p0 will be an exact
        # LSE solution for polynomial models, but we still pass to curve_fit to
        # get the covariances.
        weights = None if fit_stds is None else 1.0 / fit_stds
        func, p0, bounds = build_model_spec(name, x, y, weights)

        # Get the optimized params and covariances from curve_fit
        # evaluate_model_with_stderr will calculate the target EVs and variance estimates
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            popt, pcov = curve_fit(func, x, y, p0=p0, sigma=fit_stds, bounds=bounds)
            return evaluate_model_with_stderr(func, popt, pcov, x_eval)
    except Exception:  # pylint: disable=broad-except
        return np.full(x_eval.shape, np.nan), np.full(x_eval.shape, np.nan)


def evaluate_model_with_stderr(
    func: Callable[..., np.ndarray], popt: np.ndarray, pcov: np.ndarray, x_eval: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """Evaluate ``func`` and its delta-method uncertainty ``sqrt(J^T pcov J)`` at ``x_eval``.

    See https://www.astro.rug.nl/software/kapteyn/kmpfittutorial.html#confidence-and-prediction-intervals
    for details on estimating variance in extrapolated values.
    """
    y = np.asarray(func(x_eval, *popt), dtype=float)

    # Create the Jacobian
    jac = np.empty((y.size, len(popt)))
    for j in range(len(popt)):
        # Step size ~√ε, where ε is machine precision. This value is large enough to
        # avoid roundoff from subtracting near-equal values but small enough to faithfully
        # capture the gradient at the minima
        step = 1e-8 * max(abs(popt[j]), 1.0)
        shifted = np.array(popt, dtype=float)
        shifted[j] += step
        jac[:, j] = (np.asarray(func(x_eval, *shifted), dtype=float) - y) / step

    # Estimate the variance(s) for each extrapolated point
    var = np.einsum("ij,jk,ik->i", jac, pcov, jac)
    return y, np.sqrt(np.clip(var, 0.0, None))


def build_model_spec(
    name: str, x: np.ndarray, y: np.ndarray, weights: np.ndarray | None
) -> tuple[
    Callable[..., np.ndarray], list[float], tuple[float, float] | tuple[list[float], list[float]]
]:
    """Return ``(func, p0, bounds)`` for a builtin model name (not ``"fallback"``)."""
    # Polynomial: Linear in its parameters, so polyfit already gives the
    # exact weighted least-squares solution. We still hand it to curve_fit (as p0)
    # so the covariance is computed the same way as the exponential models.
    # Coefficients are reversed to lowest-order-first for Numpy polyval convention.
    degree = poly_degree(name)
    if degree is not None:
        p0 = list(np.polyfit(x, y, degree, w=weights)[::-1])
        return poly, p0, (-np.inf, np.inf)
    # Exponential: Nonlinear, fit by curve_fit from a log-linear seed. double_exponential sums
    # two terms and constrains every rate <= 0 (decay only).
    if name in ("exponential", "double_exponential"):
        n = 1 if name == "exponential" else 2
        decay_only = name == "double_exponential"
        p0 = seed_exp_from_log_fit(x, y, weights, n, decay_only)
        bounds = ([-np.inf, -np.inf] * n, [np.inf, 0.0] * n) if decay_only else (-np.inf, np.inf)
        return multi_exp, p0, bounds
    raise ValueError(f"Unsupported extrapolator name: {name}, must be one of {_VALID_NAMES}")


def poly(x: npt.ArrayLike, *coeffs: float) -> np.ndarray:
    """Polynomial model, coeffs should be ordered lowest-order-first."""
    return polyval(np.asarray(x, dtype=float), coeffs)


def multi_exp(x: npt.ArrayLike, *params: float) -> np.ndarray:
    """Sum of exponentials ``sum_i (a_i * exp(b_i * x))``.

    The parameter ordering should be [amp1, rate1, ...ampN, rateN].
    """
    x = np.asarray(x, dtype=float)
    out = np.zeros_like(x)
    for amp, rate in zip(params[::2], params[1::2]):
        out = out + amp * np.exp(rate * x)
    return out


def seed_exp_from_log_fit(
    x: np.ndarray, y: np.ndarray, weights: np.ndarray | None, n: int, decay_only: bool
) -> list[float]:
    """Seed ``n`` exponentials from a weight-aware log-linear fit (handles sign)."""
    # The amplitude can be negative; since a*exp(b*0) = a, infer its sign from the point
    # nearest zero noise (`or 1.0` guards the sign == 0 case).
    sgn = np.sign(y[np.argmin(x)]) or 1.0

    # The fit is in log space, so clip |y| away from zero: noise can push points to or
    # below zero, where log would blow up.
    abs_y = np.clip(np.abs(y), 1e-15, None)

    # Fit weights are ~ 1/std(y), but we fit log(y). To first order std(log y) ~
    # std(y)/|y|, so the log-space weight is |y| * weight.
    log_w = abs_y * weights if weights is not None else None

    # Recover the single-exponential seed from the line fit: slope is the rate,
    # exp(intercept) the amplitude; force a decaying rate for double exponential.
    rate, log_amp = np.polyfit(x, np.log(abs_y), 1, w=log_w)
    amp = sgn * np.exp(log_amp)
    if decay_only:
        rate = -abs(rate)

    # Equal amplitude per term so they sum to `amp`, the seed's value at x=0 (rates do
    # not affect x=0); distinct rates (multiples of the estimate) break the inter-term
    # symmetry for curve_fit.
    return [v for i in range(n) for v in (amp / n, rate * (i + 1))]


def as_noise_factors(nf: float | npt.ArrayLike | None) -> np.ndarray:
    """Coerce the extrapolated-noise-factor argument to a 1D float array."""
    if nf is None:
        return np.zeros(0)
    arr = np.atleast_1d(np.asarray(nf, dtype=float))
    if arr.ndim != 1:
        raise ValueError(
            f"Extrapolated noise factors must be a float or 1D array, not {arr.ndim}D."
        )
    return arr


def poly_degree(name: str) -> int | None:
    """Polynomial degree for a builtin name, or ``None`` if not a polynomial."""
    if name == "linear":
        return 1
    match = re.fullmatch(r"polynomial_degree_([1-7])", name)
    return int(match.group(1)) if match else None
