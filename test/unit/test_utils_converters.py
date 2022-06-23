# This code is part of Qiskit.
#
# (C) Copyright IBM 2022.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Tests for the methods utils.converters file."""

from qiskit_ibm_runtime.exceptions import IBMInputValueError
from qiskit_ibm_runtime.utils.converters import hms_to_seconds
from ..ibm_test_case import IBMTestCase


class TestUtilsConverters(IBMTestCase):
    """Tests for the methods utils.converters file."""

    def test_hms_to_seconds(self):
        """Test converting hours minutes seconds (string) to seconds (int)."""
        valid_strings = [
            ("2h", 7200),
            ("50m", 3000),
            ("20s", 20),
            ("1h 30m", 5400),
            ("3h 30m 30s", 12630),
            ("3h 30s", 10830),
            ("3h30m30s", 12630),
        ]
        invalid_strings = [
            "2d",
            "24h",
            "60m",
            "60s",
            "2w",
        ]
        for valid_string in valid_strings:
            with self.subTest(valid_string=valid_string):
                self.assertEqual(hms_to_seconds(valid_string[0]), valid_string[1])
        for invalid_string in invalid_strings:
            with self.subTest(invalid_string=invalid_string):
                with self.assertRaises(IBMInputValueError):
                    hms_to_seconds(invalid_string)
