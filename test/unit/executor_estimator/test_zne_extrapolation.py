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

"""Unit tests for the ZNE extrapolation module."""

import unittest
import warnings

import numpy as np
from ddt import data, ddt, unpack

from qiskit_ibm_runtime.executor_estimator.zne.extrapolation import (
    as_noise_factors,
    build_model_spec,
    clamp_degenerate_stds,
    evaluate_model_with_stderr,
    extrapolate,
    fit_extrapolation_models,
    multi_exp,
    poly,
    poly_degree,
    process_extrapolated_expectation_values,
    seed_exp_from_log_fit,
    select_zne_extrapolated_result,
)


@ddt
class TestPolyDegree(unittest.TestCase):
    """Tests for ``poly_degree``."""

    @data(*[(f"polynomial_degree_{k}", k) for k in range(1, 8)], ("linear", 1))
    @unpack
    def test_recognized_polynomials(self, name, degree):
        """Recognized polynomial names (including ``linear``) return their degree."""
        self.assertEqual(poly_degree(name), degree)

    @data("exponential", "double_exponential", "fallback")
    def test_non_polynomial_models(self, name):
        """Other builtin model names return ``None``."""
        self.assertIsNone(poly_degree(name))

    @data(
        "polynomial_degree_0",  # below the supported range
        "polynomial_degree_8",  # above the supported range
        "polynomial_degree_12",  # multi-digit degree
        "polynomial_degree_",  # missing degree
        "polynomial_degree",  # missing degree suffix entirely
        "polynomial_degree_1x",  # trailing junk
        "Polynomial_degree_1",  # wrong case
        "foo",  # unrelated string
        "",  # empty string
    )
    def test_unrecognized_returns_none(self, name):
        """Out-of-range, malformed, or unrelated names return ``None``."""
        self.assertIsNone(poly_degree(name))


@ddt
class TestPoly(unittest.TestCase):
    """Tests for ``poly`` (polynomial model with ascending-order coefficients)."""

    @data(1, 2, 3, 4, 5, 6, 7)
    def test_matches_ascending_polynomial(self, degree):
        """Evaluates ``sum_i coeffs[i] * x**i`` (lowest-order coefficient first)."""
        coeffs = [0.5, -0.3, 0.1, -0.05, 0.02, -0.008, 0.003, -0.001][: degree + 1]
        x = np.array([0.0, 1.0, 1.5, 2.0, 3.0])
        expected = sum(c * x**i for i, c in enumerate(coeffs))
        np.testing.assert_allclose(poly(x, *coeffs), expected)


@ddt
class TestMultiExp(unittest.TestCase):
    """Tests for ``multi_exp`` (sum of ``amp * exp(rate * x)`` over ``[amp, rate, ...]`` pairs)."""

    @data(
        (0.6, -0.3),  # single exponential (n=1)
        (0.4, -0.2, 0.3, -1.2),  # double exponential (n=2)
    )
    def test_matches_sum_of_exponentials(self, params):
        """Evaluates ``sum_i amp_i * exp(rate_i * x)`` from ``[amp, rate, ...]`` pairs."""
        x = np.array([0.0, 1.0, 1.5, 2.0, 3.0])
        amps, rates = params[::2], params[1::2]
        expected = sum(a * np.exp(b * x) for a, b in zip(amps, rates))
        np.testing.assert_allclose(multi_exp(x, *params), expected)


@ddt
class TestSeedExpFromLogFit(unittest.TestCase):
    """Tests for ``seed_exp_from_log_fit`` (seed parameters for an exponential ``curve_fit``)."""

    @data(
        # (amp, rate, n, decay_only, weights, expected)
        # exponential (n=1, decay_only=False): seed recovers (amp, rate) of a pure exponential
        (2.0, -0.5, 1, False, None, [2.0, -0.5]),  # positive amplitude
        (-3.0, 0.4, 1, False, None, [-3.0, 0.4]),  # negative amplitude, sign from the x~0 point
        (2.0, -0.5, 1, False, [1.0, 2.0, 3.0], [2.0, -0.5]),  # weighted log-linear fit
        # double_exponential (n=2, decay_only=True): amp split evenly, rates at 1x/2x, decay forced
        (4.0, -0.6, 2, True, None, [2.0, -0.6, 2.0, -1.2]),  # already decaying, rate unchanged
        (2.0, 0.5, 2, True, None, [1.0, -0.5, 1.0, -1.0]),  # growing seed forced negative
    )
    @unpack
    def test_seeds_pure_exponential(self, amp, rate, n, decay_only, weights, expected):
        """A pure ``amp * exp(rate * x)`` sample seeds the recovered parameters."""
        x = np.array([0.0, 1.0, 2.0])
        y = amp * np.exp(rate * x)
        w = None if weights is None else np.array(weights)
        result = seed_exp_from_log_fit(x, y, w, n, decay_only)
        np.testing.assert_allclose(result, expected)

    def test_zero_at_min_noise_defaults_sign_positive(self):
        """When the point nearest zero noise is 0, the amplitude sign defaults to +1."""
        x = np.array([0.0, 1.0])
        y = np.array([0.0, 1.0])
        result = seed_exp_from_log_fit(x, y, None, 1, False)
        # |y| is clipped to 1e-15 at x=0, so the log-linear seed is exact:
        # rate = 15*ln(10), amp = +exp(-15*ln(10)) = +1e-15 (positive via the sign guard)
        np.testing.assert_allclose(result, [1e-15, 15.0 * np.log(10.0)])


@ddt
class TestEvaluateModelWithStderr(unittest.TestCase):
    """Tests for ``evaluate_model_with_stderr`` (model values + delta-method standard errors)."""

    @data(
        # popt are poly ascending coeffs; pcov is the parameter covariance
        (
            [1.0, 2.0],  # y = 1 + 2x
            [[0.04, 0.01], [0.01, 0.09]],
        ),
        (
            [0.5, -1.0, 2.0],  # y = 0.5 - x + 2x**2 (exercises the |popt|>1 step branch)
            [[0.04, 0.0, 0.01], [0.0, 0.05, 0.0], [0.01, 0.0, 0.09]],
        ),
    )
    @unpack
    def test_returns_values_and_delta_method_stderr(self, popt, pcov):
        """Returns ``func(x)`` and the propagated ``sqrt(diag(J @ pcov @ J.T))``."""
        popt, pcov = np.array(popt), np.array(pcov)
        x_eval = np.array([0.0, 1.0, 2.0])
        # The delta method is exact for polynomials
        y, stderr = evaluate_model_with_stderr(poly, popt, pcov, x_eval)
        expected_y = sum(c * x_eval**i for i, c in enumerate(popt))
        # The Jacobian can be written down exactly for polynomials, and
        # the first-order variance calculation is exact for models linear
        # in their parameters.
        jac = np.vander(x_eval, len(popt), increasing=True)
        expected_var = np.einsum("ij,jk,ik->i", jac, pcov, jac)
        np.testing.assert_allclose(y, expected_y)
        np.testing.assert_allclose(stderr, np.sqrt(expected_var), rtol=1e-6)


@ddt
class TestBuildModelSpec(unittest.TestCase):
    """Tests for ``build_model_spec`` (model name -> ``(fit function, p0, bounds)``)."""

    @data(("linear", 1), *[(f"polynomial_degree_{k}", k) for k in range(1, 8)])
    @unpack
    def test_polynomial(self, name, degree):
        """Polynomial names return ``poly``, unbounded params, and an ascending-order seed."""
        coeffs = [1.0, -0.5, 0.25, -0.1, 0.05, -0.02, 0.01, -0.004][: degree + 1]
        x = np.linspace(0.0, 3.0, degree + 2)
        y = sum(c * x**i for i, c in enumerate(coeffs))
        func, p0, bounds = build_model_spec(name, x, y, None)
        self.assertIs(func, poly)
        self.assertEqual(bounds, (-np.inf, np.inf))
        # p0 is lowest-order-first, so feeding it back through poly reproduces the data
        # (a descending-order seed would not).
        np.testing.assert_allclose(poly(x, *p0), y, atol=1e-9)

    def test_exponential(self):
        """``exponential`` returns ``multi_exp``, a 2-parameter seed, and unbounded params."""
        x = np.array([0.0, 1.0, 2.0])
        y = 2.0 * np.exp(-0.5 * x)
        func, p0, bounds = build_model_spec("exponential", x, y, None)
        self.assertIs(func, multi_exp)
        self.assertEqual(len(p0), 2)
        self.assertEqual(bounds, (-np.inf, np.inf))

    def test_double_exponential(self):
        """``double_exponential`` returns a 4-parameter seed and constrains every rate <= 0."""
        x = np.array([0.0, 1.0, 2.0])
        y = 2.0 * np.exp(-0.5 * x)
        func, p0, bounds = build_model_spec("double_exponential", x, y, None)
        self.assertIs(func, multi_exp)
        self.assertEqual(len(p0), 4)
        lower, upper = bounds
        self.assertEqual(lower, [-np.inf, -np.inf, -np.inf, -np.inf])
        self.assertEqual(upper, [np.inf, 0.0, np.inf, 0.0])

    def test_unsupported_name_raises(self):
        """Names not handled here (including ``fallback``) raise ``ValueError``."""
        x = np.array([0.0, 1.0, 2.0])
        y = np.array([1.0, 0.9, 0.8])
        with self.assertRaises(ValueError):
            build_model_spec("fallback", x, y, None)


@ddt
class TestSelectZneExtrapolatedResult(unittest.TestCase):
    """Tests for ``select_zne_extrapolated_result`` (per-column model selection heuristic)."""

    @data(
        # (observable_term, values, stderrs, extraps, expected_value, expected_extrapolator)
        # Pauli basis -> range (-1, 1): highest-priority model with a non-finite value is skipped
        (
            "Z",
            [[np.nan], [0.5], [0.6]],
            [[0.1], [0.1], [0.1]],
            ["exponential", "linear", "polynomial_degree_2"],
            0.5,
            "linear",
        ),
        # projector basis -> range (0, 1): non-finite and over-threshold stderrs are rejected
        (
            "0",
            [[0.5], [0.5], [0.5]],
            [[np.inf], [2.0], [0.1]],
            ["a", "b", "c"],
            0.5,
            "c",
        ),
        # projector basis -> range (0, 1): values outside the basis range (low/high) are rejected
        (
            "0",
            [[-1.5], [2.5], [0.5]],
            [[0.1], [0.1], [0.1]],
            ["a", "b", "c"],
            0.5,
            "c",
        ),
        # none valid -> fall back to the lowest stderr (NaN stderr mapped to inf, so skipped)
        (
            "Z",
            [[0.3], [0.4], [0.5]],
            [[np.nan], [3.0], [2.0]],
            ["a", "b", "c"],
            0.5,
            "c",
        ),
        # empty observable term -> range (-inf, inf): infinite threshold accepts any finite value
        (
            "",
            [[5.0], [1.0]],
            [[10.0], [0.1]],
            ["a", "b"],
            5.0,
            "a",
        ),
    )
    @unpack
    def test_selects_valid_or_fallback(
        self, observable_term, values, stderrs, extraps, expected_value, expected_extrapolator
    ):
        """Picks the highest-priority valid model, else the lowest-stderr fallback."""
        values = np.array(values, dtype=float)
        stderrs = np.array(stderrs, dtype=float)
        res_values, res_stderrs, res_extraps = select_zne_extrapolated_result(
            values, stderrs, observable_term, extraps
        )
        self.assertEqual(res_values[0], expected_value)
        self.assertEqual(res_extraps[0], expected_extrapolator)

    def test_selects_per_column_independently(self):
        """Each noise-factor column is selected independently."""
        values = np.array([[0.2, np.nan], [0.3, 0.4]])  # basis "Z" -> range (-1, 1)
        stderrs = np.array([[0.1, 0.1], [0.1, 0.1]])
        extraps = ["exponential", "linear"]
        res_values, res_stderrs, res_extraps = select_zne_extrapolated_result(
            values, stderrs, "Z", extraps
        )
        # col 0: model 0 valid -> 0.2; col 1: model 0 is NaN -> model 1 -> 0.4
        np.testing.assert_array_equal(res_values, [0.2, 0.4])
        np.testing.assert_array_equal(res_extraps, ["exponential", "linear"])
        # output shape matches the number of extrapolation columns (not stacked)
        self.assertEqual(res_values.shape, (2,))
        self.assertEqual(res_stderrs.shape, (2,))


@ddt
class TestExtrapolate(unittest.TestCase):
    """Tests for ``extrapolate`` (one model's extrapolated values + stderrs)."""

    def test_fallback_broadcasts_lowest_noise_data(self):
        """``fallback`` returns the chosen raw point's value/stderr at every eval point."""
        y = np.array([1.0, 0.8, 0.6])
        y_std = np.array([0.1, 0.2, 0.3])
        x_eval = np.array([0.0, 0.5])
        values, stderrs = extrapolate(
            "fallback", np.array([1.0, 3.0, 5.0]), y, y_std, None, x_eval, fallback_idx=0
        )
        np.testing.assert_array_equal(values, [1.0, 1.0])
        np.testing.assert_array_equal(stderrs, [0.1, 0.1])

    @data(None, [0.1, 0.1, 0.1])
    def test_successful_fit_extrapolates(self, fit_stds):
        """A converged fit returns the model evaluated at the eval points (weighted or not)."""
        x = np.array([1.0, 3.0, 5.0])
        y = 2.0 - 0.25 * x  # exactly linear -> intercept at x=0 is 2.0
        fit_stds = None if fit_stds is None else np.array(fit_stds)
        values, stderrs = extrapolate("linear", x, y, np.full(3, 0.1), fit_stds, np.array([0.0]), 0)
        np.testing.assert_allclose(values, [2.0])
        self.assertTrue(np.all(np.isfinite(stderrs)))

    def test_fit_failure_returns_nan(self):
        """When the fit raises (here, fewer points than parameters), values/stderrs are NaN."""
        x_eval = np.array([0.0, 1.0])
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            values, stderrs = extrapolate(
                "exponential", np.array([1.0]), np.array([0.5]), np.array([0.1]), None, x_eval, 0
            )
        self.assertEqual(values.shape, x_eval.shape)
        self.assertTrue(np.all(np.isnan(values)))
        self.assertTrue(np.all(np.isnan(stderrs)))


class TestAsNoiseFactors(unittest.TestCase):
    """Tests for ``as_noise_factors`` (coerce the noise-factor argument to a 1D float array)."""

    def test_none_returns_empty(self):
        """``None`` returns an empty 1D array (no extrapolation points)."""
        out = as_noise_factors(None)
        self.assertEqual(out.shape, (0,))

    def test_multidimensional_raises(self):
        """A 2D (or higher) input raises ``ValueError``."""
        with self.assertRaises(ValueError):
            as_noise_factors([[0.0, 1.0]])


@ddt
class TestClampDegenerateStds(unittest.TestCase):
    """Tests for ``clamp_degenerate_stds``."""

    @data(
        # all positive-finite -> unchanged (each value already within [min, max] of the set)
        ([0.2, 0.4, 0.1], [0.2, 0.4, 0.1]),
        # 0 and negative -> clamped up to the smallest finite error
        ([-0.1, 0.0, 0.2, 0.4], [0.2, 0.2, 0.2, 0.4]),
        # inf and nan -> clamped down to the largest finite error (nan is not propagated)
        ([np.inf, np.nan, 0.2, 0.4], [0.4, 0.4, 0.2, 0.4]),
    )
    @unpack
    def test_clamps_degenerate_to_finite_range(self, y_std, expected):
        """Degenerate stds are clamped into the finite range; valid ones are unchanged."""
        result = clamp_degenerate_stds(np.array(y_std))
        np.testing.assert_allclose(result, expected)

    def test_all_degenerate_returns_none_with_warning(self):
        """When no std is positive and finite, returns ``None`` and warns."""
        y_std = np.array([0.0, -1.0, np.inf, np.nan])
        with self.assertWarns(UserWarning):
            result = clamp_degenerate_stds(y_std)
        self.assertIsNone(result)


class TestFitExtrapolationModels(unittest.TestCase):
    """Tests for ``fit_extrapolation_models`` (fit every model and assemble the fit arrays)."""

    _NOISE_FACTORS = np.array([1.0, 3.0, 5.0])
    _STDERRS = np.array([0.1, 0.1, 0.1])

    def test_fits_each_model_and_returns_arrays(self):
        """Each model is fit/evaluated into a row of the returned arrays."""
        values = np.array([1.75, 1.25, 0.75])  # exactly linear in the noise factors
        fit_values, fit_stderrs = fit_extrapolation_models(
            values,
            self._STDERRS,
            self._NOISE_FACTORS,
            models=["linear", "fallback"],
            extrapolated_noise_factor=0,
        )
        # row 0 = linear extrapolation to x=0 (intercept 2.0); row 1 = fallback to the
        # lowest-noise raw value (noise factor 1 -> value 1.75, stderr 0.1)
        np.testing.assert_allclose(fit_values[:, 0], [2.0, 1.75])
        self.assertAlmostEqual(fit_stderrs[1, 0], 0.1)
        # shapes: (num_models, num_extrapolated_noise_factors)
        self.assertEqual(fit_values.shape, (2, 1))
        self.assertEqual(fit_stderrs.shape, (2, 1))

    def test_unsupported_model_name_raises(self):
        """An unrecognized extrapolator name raises ``ValueError``."""
        with self.assertRaises(ValueError):
            fit_extrapolation_models(
                np.array([1.75, 1.25, 0.75]),
                self._STDERRS,
                self._NOISE_FACTORS,
                models=["not_a_model"],
            )


class TestProcessExtrapolatedExpectationValues(unittest.TestCase):
    """Tests for ``process_extrapolated_expectation_values`` (public entry point, end-to-end)."""

    # Measured values are exactly linear in the noise factors -> intercept 0.65 at x=0.
    _EXP_VALS = np.array([0.6, 0.5, 0.4])  # shape: (3 noise factors,)
    _STDERRS = np.array([0.05, 0.05, 0.05])
    _NOISE_FACTORS = [1.0, 3.0, 5.0]
    _OBSERVABLE_TERM = "Z"

    def test_end_to_end_returns_selected_values(self):
        """Returns the selected extrapolated value at the target noise factor."""
        result_vals, result_stds, result_extraps = process_extrapolated_expectation_values(
            self._EXP_VALS,
            self._STDERRS,
            self._OBSERVABLE_TERM,
            self._NOISE_FACTORS,
            ["linear", "fallback"],
            extrapolated_noise_factors=0.0,
        )
        # shape: (1 extrapolated noise factor,)
        self.assertEqual(result_vals.shape, (1,))
        np.testing.assert_allclose(result_vals[0], 0.65, rtol=1e-6)
        self.assertTrue(np.all(np.isfinite(result_stds)))
        np.testing.assert_array_equal(result_extraps[0], "linear")

    def test_string_extrapolator_is_wrapped(self):
        """A single model name (not a list) is accepted."""
        result_vals, result_stds, result_extraps = process_extrapolated_expectation_values(
            self._EXP_VALS,
            self._STDERRS,
            self._OBSERVABLE_TERM,
            self._NOISE_FACTORS,
            "linear",
            extrapolated_noise_factors=0.0,
        )
        self.assertEqual(result_vals.shape, (1,))
        np.testing.assert_allclose(result_vals[0], 0.65, rtol=1e-6)

    def test_multiple_extrapolated_noise_factors(self):
        """When multiple extrapolation targets are given, output has one entry per target."""
        result_vals, result_stds, result_extraps = process_extrapolated_expectation_values(
            self._EXP_VALS,
            self._STDERRS,
            self._OBSERVABLE_TERM,
            self._NOISE_FACTORS,
            ["linear"],
            extrapolated_noise_factors=[0.0, 1.0],
        )
        # shape: (2 extrapolated noise factors,)
        self.assertEqual(result_vals.shape, (2,))
        np.testing.assert_allclose(result_vals[0], 0.65, rtol=1e-6)
        np.testing.assert_allclose(result_vals[1], 0.6, rtol=1e-6)

    def test_unsupported_model_name_raises(self):
        """An unrecognized extrapolator name raises ``ValueError``."""
        with self.assertRaises(ValueError):
            process_extrapolated_expectation_values(
                self._EXP_VALS,
                self._STDERRS,
                self._OBSERVABLE_TERM,
                self._NOISE_FACTORS,
                ["not_a_model"],
                extrapolated_noise_factors=0.0,
            )
