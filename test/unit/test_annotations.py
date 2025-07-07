# This code is part of Qiskit.
#
# (C) Copyright IBM 2024.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Tests for runtime annotations."""

from qiskit_ibm_runtime.annotations import InjectNoise, Twirl

from ..ibm_test_case import IBMTestCase


class TestInjectNoise(IBMTestCase):
    """Test the InjectNoise class."""

    def setUp(self):
        self.inject_noise = InjectNoise("my_noise")
        super().setUp()

    def test_initialization(self):
        """Test initialization."""
        self.assertEqual(self.inject_noise.ref, "my_noise")

    def test_equality(self):
        """Test the equality method."""
        self.assertNotEqual(self.inject_noise, Twirl())
        self.assertNotEqual(self.inject_noise, InjectNoise("my_other_noise"))
        self.assertEqual(self.inject_noise, InjectNoise("my_noise"))

    def test_namespace(self):
        """Test the class is in the correct namespace."""
        self.assertEqual(InjectNoise.namespace, "runtime.inject_noise")


class TestTwirl(IBMTestCase):
    """Test the Twirl class."""

    def setUp(self):
        self.twirl = Twirl()
        self.right_rzrx_twirl = Twirl(dressing="right", decomposition="rzrx")
        super().setUp()

    def test_initialization(self):
        """Test intialization."""
        self.assertEqual(self.twirl.dressing, "left")
        self.assertEqual(self.twirl.decomposition, "rzsx")
        self.assertEqual(self.twirl.group, "pauli")

        self.assertEqual(self.right_rzrx_twirl.dressing, "right")
        self.assertEqual(self.right_rzrx_twirl.decomposition, "rzrx")

    def test_equality(self):
        """Test the equality method."""
        self.assertNotEqual(self.twirl, InjectNoise("my_noise"))
        self.assertNotEqual(self.twirl, self.right_rzrx_twirl)
        self.assertEqual(self.twirl, Twirl())

    def test_namespace(self):
        """Test the class is in the correct namespace."""
        self.assertEqual(Twirl.namespace, "runtime.twirl")
