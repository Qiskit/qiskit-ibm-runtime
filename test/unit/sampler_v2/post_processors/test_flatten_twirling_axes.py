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

"""Tests for ``flatten_twirling_axes``."""

from __future__ import annotations

import unittest

import numpy as np

from qiskit_ibm_runtime.sampler_v2.post_processors.utils import (
    flatten_twirling_axes,
)


class TestFlattenTwirlingAxes(unittest.TestCase):
    """Tests for ``flatten_twirling_axes``."""

    def test_non_parametric_pub_with_twirling(self):
        """Test flattening for a non-parametric pub (pub_shape=()) with twirling."""
        num_rand = 5
        shots_per_rand = 10
        num_bits = 3

        # Create twirled data: (num_rand, shots_per_rand, num_bits)
        data = np.random.randint(0, 2, size=(num_rand, shots_per_rand, num_bits), dtype=np.uint8)
        item = {"meas": data.copy()}

        flatten_twirling_axes(item, pub_shape=())

        # Expected shape: (total_shots, num_bits) where total_shots = num_rand * shots_per_rand
        expected_shape = (num_rand * shots_per_rand, num_bits)
        self.assertEqual(item["meas"].shape, expected_shape)

        # Verify data integrity: reshape back and compare
        reshaped = item["meas"].reshape(num_rand, shots_per_rand, num_bits)
        np.testing.assert_array_equal(reshaped, data)

    def test_1d_parametric_pub_with_twirling(self):
        """Test flattening for a 1D parametric pub (pub_shape=(3,)) with twirling."""
        num_rand = 4
        param_size = 3
        shots_per_rand = 8
        num_bits = 2

        # Create twirled data: (num_rand, param_size, shots_per_rand, num_bits)
        data = np.random.randint(
            0, 2, size=(num_rand, param_size, shots_per_rand, num_bits), dtype=np.uint8
        )
        item = {"meas": data.copy()}

        flatten_twirling_axes(item, pub_shape=(param_size,))

        # Expected shape: (param_size, total_shots, num_bits)
        expected_shape = (param_size, num_rand * shots_per_rand, num_bits)
        self.assertEqual(item["meas"].shape, expected_shape)

        # Verify data integrity: for each parameter value, shots should be concatenated correctly
        for i in range(param_size):
            # Original data for parameter i: (num_rand, shots_per_rand, num_bits)
            original_param_data = data[:, i, :, :]
            # Flattened data for parameter i: (total_shots, num_bits)
            flattened_param_data = item["meas"][i]
            # Reshape flattened back to (num_rand, shots_per_rand, num_bits)
            reshaped = flattened_param_data.reshape(num_rand, shots_per_rand, num_bits)
            np.testing.assert_array_equal(reshaped, original_param_data)

    def test_2d_parametric_pub_with_twirling(self):
        """Test flattening for a 2D parametric pub (pub_shape=(2, 3)) with twirling."""
        num_rand = 3
        pub_shape = (2, 3)
        shots_per_rand = 5
        num_bits = 4

        # Create twirled data: (num_rand, 2, 3, shots_per_rand, num_bits)
        data = np.random.randint(
            0, 2, size=(num_rand, *pub_shape, shots_per_rand, num_bits), dtype=np.uint8
        )
        item = {"meas": data.copy()}

        flatten_twirling_axes(item, pub_shape=pub_shape)

        # Expected shape: (2, 3, total_shots, num_bits)
        expected_shape = (*pub_shape, num_rand * shots_per_rand, num_bits)
        self.assertEqual(item["meas"].shape, expected_shape)

        # Verify data integrity
        for i in range(pub_shape[0]):
            for j in range(pub_shape[1]):
                original_param_data = data[:, i, j, :, :]
                flattened_param_data = item["meas"][i, j]
                reshaped = flattened_param_data.reshape(num_rand, shots_per_rand, num_bits)
                np.testing.assert_array_equal(reshaped, original_param_data)

    def test_multiple_classical_registers(self):
        """Test flattening with multiple classical registers."""
        num_rand = 4
        pub_shape = (2,)
        shots_per_rand = 6

        # Create twirled data for multiple registers with different bit counts
        data1 = np.random.randint(
            0, 2, size=(num_rand, *pub_shape, shots_per_rand, 3), dtype=np.uint8
        )
        data2 = np.random.randint(
            0, 2, size=(num_rand, *pub_shape, shots_per_rand, 5), dtype=np.uint8
        )

        item = {"creg1": data1.copy(), "creg2": data2.copy()}

        flatten_twirling_axes(item, pub_shape=pub_shape)

        # Both registers should be flattened
        expected_shape1 = (*pub_shape, num_rand * shots_per_rand, 3)
        expected_shape2 = (*pub_shape, num_rand * shots_per_rand, 5)

        self.assertEqual(item["creg1"].shape, expected_shape1)
        self.assertEqual(item["creg2"].shape, expected_shape2)

    def test_data_ordering_preserved(self):
        """Test that the order of shots is preserved correctly after flattening."""
        # Create data with known values to verify ordering
        # Shape: (num_rand=3, shots_per_rand=2, num_bits=1)
        data = np.array(
            [
                [[0], [1]],  # rand 0: shots 0, 1
                [[2], [3]],  # rand 1: shots 0, 1
                [[4], [5]],  # rand 2: shots 0, 1
            ],
            dtype=np.uint8,
        )

        item = {"meas": data}
        flatten_twirling_axes(item, pub_shape=())

        # After flattening, shots should be ordered as:
        # rand0_shot0, rand0_shot1, rand1_shot0, rand1_shot1, rand2_shot0, rand2_shot1
        expected = np.array([[0], [1], [2], [3], [4], [5]], dtype=np.uint8)
        np.testing.assert_array_equal(item["meas"], expected)
