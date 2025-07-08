# This code is part of Qiskit.
#
# (C) Copyright IBM 2025.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Tests for Distribute class."""

import ddt

import numpy as np
import numpy.testing as npt

from qiskit_ibm_runtime.options.distribute import Distribute

from ..ibm_test_case import IBMTestCase


@ddt.ddt
class TestDistribute(IBMTestCase):
    """Class for testing Distribute."""

    def setUp(self):
        super().setUp()
        self.distribute = Distribute(1, [[1, 2, 3], [4, 5, 6]], np.array([1, 2, 3]))

    def test_initialization(self):
        """Test intialization."""
        self.assertEqual(len(self.distribute), 3)
        self.assertEqual(self.distribute[0], 1)
        npt.assert_array_equal(self.distribute[1], np.array([[1, 2, 3], [4, 5, 6]]))
        npt.assert_array_equal(self.distribute[2], np.array([1, 2, 3]))

    def test_equality(self):
        """Test the equality method."""
        self.assertNotEqual(self.distribute, 1)
        self.assertNotEqual(self.distribute, Distribute(1))
        self.assertNotEqual(
            self.distribute, Distribute(1, [[1, 2, 3], [4, 5, 6]]), np.array([1, 2, 2])
        )
        self.assertEqual(
            self.distribute, Distribute(1, [[1, 2, 3], [4, 5, 6]], np.array([1, 2, 3]))
        )

    def test_repr(self):
        """Test the repr method."""
        self.assertEqual(repr(self.distribute), "Distribute(<3>)")

    @ddt.data((0, ()), (1, (2, 3)), (2, (3,)))
    @ddt.unpack
    def test_shape(self, idx, shape):
        """Test the shape method."""
        self.assertEqual(self.distribute.shape(idx), shape)
