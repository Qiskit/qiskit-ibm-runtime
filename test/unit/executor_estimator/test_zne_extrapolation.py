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

import numpy as np
from ddt import data, ddt, unpack

from qiskit_ibm_runtime.executor_estimator.zne.extrapolation import (
    _as_noise_factors,
    _build_model_spec,
    _clamp_degenerate_stds,
    _copy_metadata,
    _evaluate_model_with_stderr,
    _multi_exp,
    _poly,
    _poly_degree,
    _seed_exp_from_log_fit,
)


@ddt
class TestPolyDegree(unittest.TestCase):
    """Tests for ``_poly_degree``."""

    @data(*[(f"polynomial_degree_{k}", k) for k in range(1, 8)], ("linear", 1))
    @unpack
    def test_recognized_polynomials(self, name, degree):
        """Recognized polynomial names (including ``linear``) return their degree."""
        self.assertEqual(_poly_degree(name), degree)

    @data("exponential", "double_exponential", "fallback")
    def test_non_polynomial_models(self, name):
        """Other builtin model names return ``None``."""
        self.assertIsNone(_poly_degree(name))

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
        self.assertIsNone(_poly_degree(name))


@ddt
class TestPoly(unittest.TestCase):
    """Tests for ``_poly`` (polynomial model with ascending-order coefficients)."""

    @data(1, 2, 3, 4, 5, 6, 7)
    def test_matches_ascending_polynomial(self, degree):
        """Evaluates ``sum_i coeffs[i] * x**i`` (lowest-order coefficient first)."""
        coeffs = [0.5, -0.3, 0.1, -0.05, 0.02, -0.008, 0.003, -0.001][: degree + 1]
        x = np.array([0.0, 1.0, 1.5, 2.0, 3.0])
        expected = sum(c * x**i for i, c in enumerate(coeffs))
        np.testing.assert_allclose(_poly(x, *coeffs), expected)


@ddt
class TestMultiExp(unittest.TestCase):
    """Tests for ``_multi_exp`` (sum of ``amp * exp(rate * x)`` over ``[amp, rate, ...]`` pairs)."""

    @data(
        (0.6, -0.3),  # single exponential (n=1)
        (0.4, -0.2, 0.3, -1.2),  # double exponential (n=2)
    )
    def test_matches_sum_of_exponentials(self, params):
        """Evaluates ``sum_i amp_i * exp(rate_i * x)`` from ``[amp, rate, ...]`` pairs."""
        x = np.array([0.0, 1.0, 1.5, 2.0, 3.0])
        amps, rates = params[::2], params[1::2]
        expected = sum(a * np.exp(b * x) for a, b in zip(amps, rates))
        np.testing.assert_allclose(_multi_exp(x, *params), expected)


@ddt
class TestSeedExpFromLogFit(unittest.TestCase):
    """Tests for ``_seed_exp_from_log_fit`` (seed parameters for an exponential ``curve_fit``)."""

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
        result = _seed_exp_from_log_fit(x, y, w, n, decay_only)
        np.testing.assert_allclose(result, expected)

    def test_zero_at_min_noise_defaults_sign_positive(self):
        """When the point nearest zero noise is 0, the amplitude sign defaults to +1."""
        x = np.array([0.0, 1.0])
        y = np.array([0.0, 1.0])
        result = _seed_exp_from_log_fit(x, y, None, 1, False)
        # |y| is clipped to 1e-15 at x=0, so the log-linear seed is exact:
        # rate = 15*ln(10), amp = +exp(-15*ln(10)) = +1e-15 (positive via the sign guard)
        np.testing.assert_allclose(result, [1e-15, 15.0 * np.log(10.0)])


@ddt
class TestEvaluateModelWithStderr(unittest.TestCase):
    """Tests for ``_evaluate_model_with_stderr`` (model values + delta-method standard errors)."""

    @data(
        # popt are _poly ascending coeffs; pcov is the parameter covariance
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
        y, stderr = _evaluate_model_with_stderr(_poly, popt, pcov, x_eval)
        expected_y = sum(c * x_eval**i for i, c in enumerate(popt))
        jac = np.vander(x_eval, len(popt), increasing=True)
        expected_var = np.einsum("ij,jk,ik->i", jac, pcov, jac)
        np.testing.assert_allclose(y, expected_y)
        np.testing.assert_allclose(stderr, np.sqrt(expected_var), rtol=1e-6)


@ddt
class TestBuildModelSpec(unittest.TestCase):
    """Tests for ``_build_model_spec`` (model name -> ``(fit function, p0, bounds)``)."""

    @data(("linear", 1), *[(f"polynomial_degree_{k}", k) for k in range(1, 8)])
    @unpack
    def test_polynomial(self, name, degree):
        """Polynomial names return ``_poly``, unbounded params, and an ascending-order seed."""
        coeffs = [1.0, -0.5, 0.25, -0.1, 0.05, -0.02, 0.01, -0.004][: degree + 1]
        x = np.linspace(0.0, 3.0, degree + 2)
        y = sum(c * x**i for i, c in enumerate(coeffs))
        func, p0, bounds = _build_model_spec(name, x, y, None)
        self.assertIs(func, _poly)
        self.assertEqual(bounds, (-np.inf, np.inf))
        # p0 is lowest-order-first, so feeding it back through _poly reproduces the data
        # (a descending-order seed would not).
        np.testing.assert_allclose(_poly(x, *p0), y, atol=1e-9)

    def test_exponential(self):
        """``exponential`` returns ``_multi_exp``, a 2-parameter seed, and unbounded params."""
        x = np.array([0.0, 1.0, 2.0])
        y = 2.0 * np.exp(-0.5 * x)
        func, p0, bounds = _build_model_spec("exponential", x, y, None)
        self.assertIs(func, _multi_exp)
        self.assertEqual(len(p0), 2)
        self.assertEqual(bounds, (-np.inf, np.inf))

    def test_double_exponential(self):
        """``double_exponential`` returns a 4-parameter seed and constrains every rate <= 0."""
        x = np.array([0.0, 1.0, 2.0])
        y = 2.0 * np.exp(-0.5 * x)
        func, p0, bounds = _build_model_spec("double_exponential", x, y, None)
        self.assertIs(func, _multi_exp)
        self.assertEqual(len(p0), 4)
        lower, upper = bounds
        self.assertEqual(lower, [-np.inf, -np.inf, -np.inf, -np.inf])
        self.assertEqual(upper, [np.inf, 0.0, np.inf, 0.0])

    def test_unsupported_name_raises(self):
        """Names not handled here (including ``fallback``) raise ``ValueError``."""
        x = np.array([0.0, 1.0, 2.0])
        y = np.array([1.0, 0.9, 0.8])
        with self.assertRaises(ValueError):
            _build_model_spec("fallback", x, y, None)


@ddt
class TestAsNoiseFactors(unittest.TestCase):
    """Tests for ``_as_noise_factors`` (coerce the noise-factor argument to a 1D float array)."""

    @data(
        (0, [0.0]),  # scalar (the default) -> length-1, int coerced to float
        ([0.0, 0.5, 1.0], [0.0, 0.5, 1.0]),  # 1D sequence -> unchanged
    )
    @unpack
    def test_coerces_to_1d_float_array(self, nf, expected):
        """Scalars and 1D sequences become a 1D float array."""
        out = _as_noise_factors(nf)
        self.assertEqual(out.ndim, 1)
        self.assertTrue(np.issubdtype(out.dtype, np.floating))
        np.testing.assert_allclose(out, expected)

    def test_none_returns_empty(self):
        """``None`` returns an empty 1D array (no extrapolation points)."""
        out = _as_noise_factors(None)
        self.assertEqual(out.shape, (0,))

    def test_multidimensional_raises(self):
        """A 2D (or higher) input raises ``ValueError``."""
        with self.assertRaises(ValueError):
            _as_noise_factors([[0.0, 1.0]])


@ddt
class TestClampDegenerateStds(unittest.TestCase):
    """Tests for ``_clamp_degenerate_stds``."""

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
        result = _clamp_degenerate_stds(np.array(y_std))
        np.testing.assert_allclose(result, expected)

    def test_all_degenerate_returns_none_with_warning(self):
        """When no std is positive and finite, returns ``None`` and warns."""
        y_std = np.array([0.0, -1.0, np.inf, np.nan])
        with self.assertWarns(UserWarning):
            result = _clamp_degenerate_stds(y_std)
        self.assertIsNone(result)


class TestCopyMetadata(unittest.TestCase):
    """Tests for ``_copy_metadata`` (recursive copy of nested metadata dicts)."""

    def test_nested_dicts_are_independent(self):
        """Every dict level is a fresh object, so popping from the copy spares the original."""
        original = {
            "standard_error": np.array([0.02, 0.03]),
            "ev_basis": "Z",
            "resilience": {"zne_noise_factors": np.array([1.0, 2.0])},
        }
        copied = _copy_metadata(original)

        self.assertEqual(copied.keys(), original.keys())
        self.assertIsNot(copied, original)
        self.assertIsNot(copied["resilience"], original["resilience"])
        # popping from the copy (as the caller does) leaves the original intact
        copied.pop("standard_error")
        copied["resilience"].pop("zne_noise_factors")
        self.assertIn("standard_error", original)
        self.assertIn("zne_noise_factors", original["resilience"])
