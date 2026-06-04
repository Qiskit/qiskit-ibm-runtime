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

"""Zero-noise extrapolation (ZNE) post-processing of estimator results.

Fits extrapolation models to expectation values measured at several noise
factors and evaluates them at zero (or other) noise factors using
``scipy.optimize.curve_fit``. :func:`process_extrapolated_expectation_values`
is the module entry point.
"""

from __future__ import annotations

import re
import warnings
from typing import TYPE_CHECKING, Any

import numpy as np
from numpy.polynomial.polynomial import polyval as _polyval
from qiskit.primitives import EstimatorResult
from scipy.optimize import curve_fit

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from numpy.typing import ArrayLike


_VALID_NAMES = [
    "linear",
    "exponential",
    "double_exponential",
    "polynomial_degree_(1 <= k <= 7)",
    "fallback",
]


def process_extrapolated_expectation_values(
    result: EstimatorResult,
    extrapolator: str | Sequence[str],
    extrapolated_noise_factors: float | ArrayLike = 0,
) -> EstimatorResult:
    r"""Apply zero-noise extrapolation (ZNE) to an estimator result.

    For each result, the requested model(s) are fit to the expectation values measured at
    the result's noise factors and evaluated at the target noise factor(s) (``0`` for zero
    noise). Models are tried in priority order: each point takes the result of the
    first model whose extrapolation is valid. A valid extrapolation results in a finite
    value and standard error, with the :math:`value \pm stderr` plausible with respect to
    the measurement basis. If no models produce a valid value, the measured input value with
    the smallest standard error will be returned.

    The standard errors reported for the extrapolated values are first-order estimates
    propagated from the fit covariance. For details see the `confidence and prediction intervals
    section of this kapteyn tutorial`
    <https://www.astro.rug.nl/software/kapteyn/kmpfittutorial.html#confidence-and-prediction-intervals>`_.

    Args:
        result: Estimator result whose per-entry metadata provides ``standard_error`` and a
            ``resilience["zne_noise_factors"]`` array, with values measured at those factors.
        extrapolator: A builtin model name, or a sequence of names tried in priority order.
            Supported: ``linear``, ``exponential``, ``double_exponential``,
            ``polynomial_degree_k`` (1 <= k <= 7), and ``fallback`` (no fit; returns the
            input measurement with the smallest standard error).
        extrapolated_noise_factors: Scalar or 1D array of noise factors to evaluate the fits
            at; defaults to ``0`` (zero-noise extrapolation).

    Raises:
        ValueError: If an entry is missing ``standard_error`` or ``zne_noise_factors``
            metadata, or if an extrapolator name is not recognized.

    Returns:
        A new estimator result. Per entry, ``values`` is a 2D array stacking the selected
        extrapolation (row 0) above each model's extrapolation (rows 1+), with the raw
        measured noise-factor values appended along the last axis; ``standard_error`` and the
        ``resilience`` ``zne_noise_factors``/``zne_extrapolator`` fields are reshaped to
        match. A size-1 result collapses to a scalar.
    """
    if isinstance(extrapolator, str):
        extrapolator = [extrapolator]

    result_values = []
    result_metadata = []
    for raw_values, raw_metadata in zip(result.values, result.metadata):
        if "zne_noise_factors" not in raw_metadata.get("resilience", {}):
            raise ValueError("`zne_noise_factors` is missing from the `resilience` metadata")
        if "standard_error" not in raw_metadata:
            raise ValueError("`standard_error` is missing from the result metadata")

        # Get 2D array of extrapolated EVs and associated metadata.
        # Array shape: (# extrapolators, # extrapolated noise factors)
        fit_values, fit_metadata = _fit_extrapolation_models(
            raw_values,
            raw_metadata,
            models=extrapolator,
            extrapolated_noise_factor=extrapolated_noise_factors,
        )
        # Stack the selected EVs for each noise scale in the top row of fit_values and
        # adjust metadata to account for the new shape of output.
        fit_values, fit_metadata = _select_zne_extrapolated_result(fit_values, fit_metadata)
        fit_values, fit_metadata = _stack_unextrapolated_result(
            fit_values, fit_metadata, raw_values, raw_metadata
        )
        fit_values, fit_metadata = _format_extrapolated(fit_values, fit_metadata)

        result_values.append(fit_values)
        result_metadata.append(fit_metadata)

    return EstimatorResult(result_values, result_metadata)


def _fit_extrapolation_models(
    values: ArrayLike,
    metadata: dict[str, Any],
    models: Sequence[str],
    extrapolated_noise_factor: float | ArrayLike = 0,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Fit each model to the noise-scaled data and evaluate at the extrapolation points.

    Returns ``(fit_values, fit_metadata)`` where ``fit_values`` is a 2D array whose
    first axis indexes the model and second axis the extrapolated noise factor.
    """
    fit_metadata = _copy_metadata(metadata)
    if "resilience" not in fit_metadata:
        raise ValueError("`resilience` metadata is missing.")

    y_data = np.asarray(values, dtype=float)
    y_std = np.asarray(fit_metadata.pop("standard_error"), dtype=float)
    x_data = np.asarray(fit_metadata["resilience"].pop("zne_noise_factors"), dtype=float)
    fit_metadata.pop("ensemble_standard_error", None)

    # Make noise factor(s) arrays
    x_eval = _as_noise_factors(extrapolated_noise_factor)

    # Clamp negative/0.0 stds to min(y_std). Clamp inf/NaN stds to max(y_std).
    # If no valid stds, function returns None
    fit_stds = _clamp_degenerate_stds(y_std)

    # Ensure the extrapolators are valid
    names = list(models)
    for name in names:
        if (
            name != "fallback"
            and _poly_degree(name) is None
            and name
            not in (
                "exponential",
                "double_exponential",
            )
        ):
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
        fit_values[i], fit_stderrs[i] = _extrapolate(
            name, x_data, y_data, y_std, fit_stds, x_eval, fallback_idx
        )

    # Set up metadata arrays
    extrapolators = np.empty((len(names), x_eval.size), dtype=object)
    for i, name in enumerate(names):
        extrapolators[i] = name
    fit_metadata["standard_error"] = fit_stderrs
    fit_metadata["resilience"]["zne_noise_factors"] = np.broadcast_to(
        x_eval, fit_values.shape
    ).copy()
    fit_metadata["resilience"]["zne_extrapolator"] = extrapolators

    return fit_values, fit_metadata


def _clamp_degenerate_stds(y_std: np.ndarray) -> np.ndarray | None:
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


def _select_zne_extrapolated_result(
    zne_values: np.ndarray, zne_metadata: dict[str, Any]
) -> tuple[np.ndarray, dict[str, Any]]:
    """Choose the best extrapolated values and stack them in the top row of the values/metadata.

    The best value is the valid value produced by the highest-priority model. Valid values are
    those that are finite, have a standard error within the measurement-basis threshold, and lie
    within the basis's range to within that standard error.

    Modifies metadata in place.
    """
    # Patterns for matching ev bases for range of ideal outcomes.
    # Range [0, 1] for basis containing only I and projectors.
    # Range [-1, 1] for bases containing non-I Paulis.
    _pattern_ylim_01 = re.compile(r"^[I01lr+\-]+$")
    _pattern_ylim_pm1 = re.compile(r"^[XYZI01lr+\-]+$")
    zne_stderrs = zne_metadata["standard_error"]
    zne_nfs = zne_metadata["resilience"]["zne_noise_factors"]
    zne_extrap = zne_metadata["resilience"]["zne_extrapolator"]

    # Determine ideal value limits for standard basis projectors. If there is any
    # Pauli in the basis term we assume ideal <B> in [-1, 1], otherwise [0, 1].
    basis = zne_metadata.get("ev_basis", "")
    if re.search(_pattern_ylim_01, basis):
        val_min, val_max = (0, 1)
    elif re.search(_pattern_ylim_pm1, basis):
        val_min, val_max = (-1, 1)
    else:
        val_min, val_max = (-np.inf, np.inf)

    # Filter candidate values that have non-finite values/std errors and values
    # with standard errors outside the basis threshold.
    stderr_threshold = max(abs(val_min), abs(val_max))
    reject_conditions = np.stack(
        [
            np.logical_not(np.isfinite(zne_values)),
            np.logical_not(np.isfinite(zne_stderrs)),
            zne_stderrs > stderr_threshold,
            zne_values - zne_stderrs < val_min - stderr_threshold,
            zne_values + zne_stderrs > val_max + stderr_threshold,
        ],
        axis=-1,
    )
    accept = np.logical_not(np.any(reject_conditions, axis=-1))

    # Fallback index is the lowest stderror result if none satisfy acceptance
    # criteria. Here we map NaN to Inf since argmin treats NaN < 0.
    fallback_indices = np.argmin(np.nan_to_num(zne_stderrs, nan=np.inf), axis=0)

    # Iterate across each extrapolated noise scale and select the output from the
    # highest-priority (lowest indexed) model that produced a valid output.
    # If no model gives a valid output for a noise scale, the value with the lowest
    # stderr will be chosen.
    accept_values = np.zeros(zne_values.shape[1:], dtype=float)
    accept_stderrs = np.zeros_like(accept_values)
    accept_nfs = np.zeros_like(accept_values)
    accept_extrap = np.zeros_like(accept_values, dtype=object)
    for idx, col in enumerate(accept.T):
        accepted = np.where(col)[0]
        fits_idx = (accepted[0], idx) if accepted.size else (fallback_indices[idx], idx)
        accept_values[idx] = zne_values[fits_idx]
        accept_stderrs[idx] = zne_stderrs[fits_idx]
        accept_extrap[idx] = zne_extrap[fits_idx]
        accept_nfs[idx] = zne_nfs[fits_idx]

    # Stack the row of selected extrapolated values on top of the original values.
    res_values = np.vstack([[accept_values], zne_values])
    res_stderrs = np.vstack([[accept_stderrs], zne_stderrs])
    res_nfs = np.vstack([[accept_nfs], zne_nfs])
    res_extrap = np.vstack([[accept_extrap], zne_extrap])

    # Update the metadata to contain the data with the selected values in the first row
    zne_metadata["standard_error"] = res_stderrs
    zne_metadata["resilience"]["zne_noise_factors"] = res_nfs
    zne_metadata["resilience"]["zne_extrapolator"] = res_extrap

    return res_values, zne_metadata


def _extrapolate(
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
        func, p0, bounds = _model(name, x, y, weights)

        # Get the optimized params and covariances from curve_fit
        # _eval_model will calculate the target EVs and variance estimates
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            popt, pcov = curve_fit(func, x, y, p0=p0, sigma=fit_stds, bounds=bounds)
            return _eval_model(func, popt, pcov, x_eval)
    except Exception:  # pylint: disable=broad-except
        return np.full(x_eval.shape, np.nan), np.full(x_eval.shape, np.nan)


def _eval_model(
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


def _model(
    name: str, x: np.ndarray, y: np.ndarray, weights: np.ndarray | None
) -> tuple[
    Callable[..., np.ndarray], list[float], tuple[float, float] | tuple[list[float], list[float]]
]:
    """Return ``(func, p0, bounds)`` for a builtin model name (not ``"fallback"``)."""
    # Polynomial: Linear in its parameters, so polyfit already gives the
    # exact weighted least-squares solution. We still hand it to curve_fit (as p0)
    # so the covariance is computed the same way as the exponential models.
    # Coefficients are reversed to lowest-order-first for Numpy polyval convention.
    degree = _poly_degree(name)
    if degree is not None:
        p0 = list(np.polyfit(x, y, degree, w=weights)[::-1])
        return _poly, p0, (-np.inf, np.inf)
    # Exponential: Nonlinear, fit by curve_fit from a log-linear seed. double_exponential sums
    # two terms and constrains every rate <= 0 (decay only).
    if name in ("exponential", "double_exponential"):
        n = 1 if name == "exponential" else 2
        decay_only = name == "double_exponential"
        p0 = _exp_guess(x, y, weights, n, decay_only)
        bounds = ([-np.inf, -np.inf] * n, [np.inf, 0.0] * n) if decay_only else (-np.inf, np.inf)
        return _multi_exp, p0, bounds
    raise ValueError(f"Unsupported extrapolator name: {name}, must be one of {_VALID_NAMES}")


def _poly(x: ArrayLike, *coeffs: float) -> np.ndarray:
    """Polynomial model, coeffs should be ordered lowest-order-first."""
    return _polyval(np.asarray(x, dtype=float), coeffs)


def _multi_exp(x: ArrayLike, *params: float) -> np.ndarray:
    """Sum of exponentials ``sum_i (a_i * exp(b_i * x))``.

    The parameter ordering should be [amp1, rate1, ...ampN, rateN].
    """
    x = np.asarray(x, dtype=float)
    out = np.zeros_like(x)
    for amp, rate in zip(params[::2], params[1::2]):
        out = out + amp * np.exp(rate * x)
    return out


def _exp_guess(
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


def _stack_unextrapolated_result(
    zne_values: np.ndarray,
    zne_metadata: dict[str, Any],
    raw_values: np.ndarray,
    raw_metadata: dict[str, Any],
) -> tuple[np.ndarray, dict[str, Any]]:
    """Concatenate the un-extrapolated noise-factor data onto the extrapolated result."""

    def _concatenate_rows(arr: np.ndarray, row: np.ndarray) -> np.ndarray:
        if arr.size == 0:
            return row
        bcast = np.broadcast_to(row, arr.shape[:-1] + row.shape)
        return np.concatenate([arr, bcast], axis=-1)

    stacked_values = _concatenate_rows(zne_values, raw_values)
    stacked_metadata = zne_metadata
    stacked_metadata["standard_error"] = _concatenate_rows(
        zne_metadata["standard_error"], raw_metadata["standard_error"]
    )
    if "ensemble_standard_error" in raw_metadata:
        # The ZNE extrapolated data doesn't define an ensemble standard error so we set it to NaN.
        stacked_metadata["ensemble_standard_error"] = _concatenate_rows(
            np.nan * np.ones_like(zne_values), raw_metadata["ensemble_standard_error"]
        )
    stacked_metadata["resilience"]["zne_noise_factors"] = _concatenate_rows(
        zne_metadata["resilience"]["zne_noise_factors"],
        raw_metadata["resilience"]["zne_noise_factors"],
    )
    # The extrapolator field has no value for the raw (un-extrapolated) rows, so pad with None.
    if "zne_extrapolator" in zne_metadata["resilience"]:
        none_vals = np.array(len(raw_values) * [None], dtype=object)
        stacked_metadata["resilience"]["zne_extrapolator"] = _concatenate_rows(
            zne_metadata["resilience"]["zne_extrapolator"], none_vals
        )
    return stacked_values, stacked_metadata


def _as_noise_factors(nf: float | ArrayLike | None) -> np.ndarray:
    """Coerce the extrapolated-noise-factor argument to a 1D float array."""
    if nf is None:
        return np.zeros(0)
    arr = np.atleast_1d(np.asarray(nf, dtype=float))
    if arr.ndim != 1:
        raise ValueError(
            f"Extrapolated noise factors must be a float or 1D array, not {arr.ndim}D."
        )
    return arr


def _poly_degree(name: str) -> int | None:
    """Polynomial degree for a builtin name, or ``None`` if not a polynomial."""
    if name == "linear":
        return 1
    match = re.fullmatch(r"polynomial_degree_([1-7])", name)
    return int(match.group(1)) if match else None


def _format_extrapolated(
    fit_values: np.ndarray, fit_metadata: dict[str, Any]
) -> tuple[float | np.ndarray, dict[str, Any]]:
    """Reshape size-1 results to floats to avoid returning shaped results in that case."""
    if fit_values.size == 1:
        fit_values = fit_values.flat[0]
        fit_metadata["standard_error"] = fit_metadata["standard_error"].flat[0]
        if "ensemble_standard_error" in fit_metadata:
            fit_metadata["ensemble_standard_error"] = fit_metadata["ensemble_standard_error"].flat[
                0
            ]
        res = fit_metadata["resilience"]
        for field in ["zne_noise_factors", "zne_extrapolator"]:
            if field in res:
                res[field] = res[field].flat[0]
    return fit_values, fit_metadata


def _copy_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    """Safer shallow copy of nested metadata."""
    return {
        key: _copy_metadata(value) if isinstance(value, dict) else value
        for key, value in metadata.items()
    }
