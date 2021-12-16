# This code is part of Qiskit.
#
# (C) Copyright IBM 2021.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Tests for utils."""

from qiskit_ibm_runtime.utils import is_crn, crn_to_api_host
from qiskit_ibm_runtime import CannotMapCrnToApiHostError

from ..ibm_test_case import IBMTestCase


CRN_HOST_TUPLES = [
    [
        "crn:v1:bluemix:public:quantum-computing:us-east:a/...::",
        "https://us-east.quantum-computing.cloud.ibm.com",
    ]
]


class TestUtils(IBMTestCase):
    """Tests for utility functions."""

    def test_is_crn(self):
        """Tests detection of CRN values."""
        self.assertFalse(is_crn("abc"))
        for entry in CRN_HOST_TUPLES:
            self.assertTrue(is_crn(entry[0]))

    def test_map_to_api_host(self):
        """Tests mapping of CRN values to API hosts."""
        for entry in CRN_HOST_TUPLES:
            print(entry)
            print(crn_to_api_host(entry[0]))
            self.assertEqual(crn_to_api_host(entry[0]), entry[1])

        self.assertRaises(
            CannotMapCrnToApiHostError, lambda: crn_to_api_host("invalid")
        )
