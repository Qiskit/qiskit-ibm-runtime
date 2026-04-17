# This code is part of Qiskit.
#
# (C) Copyright IBM 2021-2026.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Tests for the functions in the utils file."""

from qiskit.qpy import QPY_VERSION
from samplomatic.ssv import SSV

from qiskit_ibm_runtime.utils.utils import get_qpy_version, get_ssv_version
from ...ibm_test_case import IBMTestCase


class TestGetQPYVersion(IBMTestCase):
    """Test for getter of QPY version."""

    def test_no_highest_value(self):
        """Test with unset highest value."""
        self.assertEqual(get_qpy_version(), QPY_VERSION)

    def test_highest_value(self):
        """Test with set highest value."""
        self.assertEqual(get_qpy_version(1), 1)


class TestGetSSVersion(IBMTestCase):
    """Test for getter of SSV version."""

    def test_no_highest_value(self):
        """Test with unset highest value."""
        self.assertEqual(get_ssv_version(), SSV)

    def test_highest_value(self):
        """Test with set highest value."""
        self.assertEqual(get_ssv_version(1), 1)
