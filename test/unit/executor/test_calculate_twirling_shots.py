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

"""Tests for calculate twirling shots function."""

import unittest

from ddt import ddt, data, unpack

from qiskit_ibm_runtime.executor.calculate_twirling_shots import (
    calculate_twirling_shots,
)


@ddt
class TestCalculateTwirlingShots(unittest.TestCase):
    """Tests for calculate_twirling_shots function."""

    @data(
        # (shots, n_rand, shots_per_rand, expected_n_rand, expected_shots_per_rand)
        # Both auto
        (1000, "auto", "auto", 16, 64),
        (10000, "auto", "auto", 32, 313),
        # Only num_randomizations auto
        (1000, "auto", 100, 10, 100),
        # Only shots_per_randomization auto
        (1000, 20, "auto", 20, 50),
        # Both specified
        (1000, 25, 40, 25, 40),
    )
    @unpack
    def test_calculate_twirling_shots(
        self,
        pub_shots,
        num_randomizations,
        shots_per_randomization,
        expected_num_rand,
        expected_shots_per_rand,
    ):
        """Test calculate_twirling_shots with various parameter combinations."""
        num_rand, shots_per_rand = calculate_twirling_shots(
            pub_shots, num_randomizations, shots_per_randomization
        )

        self.assertEqual(num_rand, expected_num_rand)
        self.assertEqual(shots_per_rand, expected_shots_per_rand)
        self.assertIsInstance(num_rand, int)
        self.assertIsInstance(shots_per_rand, int)
