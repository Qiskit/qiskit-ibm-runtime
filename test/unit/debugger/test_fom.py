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

"""Tests for the debugger's figures of merit."""

from ddt import ddt
import numpy as np

from qiskit.primitives.containers import PrimitiveResult, PubResult, DataBin
from qiskit_ibm_runtime.debugger import Ratio

from ...ibm_test_case import IBMTestCase


@ddt
class TestRatio(IBMTestCase):
    """Class for testing the Ratio class."""

    def setUp(self):
        super().setUp()

        self.r1 = PrimitiveResult([PubResult(DataBin(evs=[1, 2, 3]))])
        self.r2 = PrimitiveResult([PubResult(DataBin(evs=[2, 4, 6]))])
        self.r4 = PrimitiveResult([PubResult(DataBin(evs=[1, 2])), PubResult(DataBin(evs=[3, 4]))])
        self.r5 = PrimitiveResult([PubResult(DataBin(evs=[1, 4])), PubResult(DataBin(evs=[9, 16]))])

    def test_ratio(self):
        r"""
        Tests that Ratio works as expected.
        """
        self.assertListEqual(Ratio(self.r1, self.r2), [[0.5, 0.5, 0.5]])
        self.assertListEqual(Ratio(self.r5, self.r4), [[1, 2], [3, 4]])

    def test_zero_at_denominator(self):
        r"""
        Tests that Ratio returns `0` when it finds `0` at the denominator.
        """
        r = PrimitiveResult([PubResult(DataBin(evs=[0, 0, 1]))])
        self.assertListEqual(Ratio(self.r1, r), [[0, 0, 3]])

    def test_ratio_error(self):
        r"""
        Tests that Ratio errors when the shapes are not consistent.
        """
        with self.assertRaises(ValueError):
            Ratio(self.r1, self.r4)
