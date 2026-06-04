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
    _clamp_degenerate_stds,
    _copy_metadata,
    _multi_exp,
    _poly,
    _poly_degree,
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

    def test_leaf_values_are_shared_not_deep_copied(self):
        """Non-dict leaf values (e.g. arrays) are referenced, not duplicated."""
        std = np.array([0.02, 0.03])
        original = {"standard_error": std, "resilience": {"foo": std}}
        copied = _copy_metadata(original)
        self.assertIs(copied["standard_error"], std)
        self.assertIs(copied["resilience"]["foo"], std)
