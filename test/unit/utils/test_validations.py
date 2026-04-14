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

"""Tests for validation functions."""

import numpy as np

from qiskit_ibm_runtime.utils.validations import is_datatree_compatible
from ...ibm_test_case import IBMTestCase


class TestIsDatatreeCompatible(IBMTestCase):
    """Test for is_datatree_compatible function."""

    def test_valid_datatree_structures(self):
        """Test that valid DataTree structures return True."""
        # Test all valid types in a nested structure
        valid_data = {
            "string": "value",
            "int": 42,
            "float": 3.14,
            "bool": True,
            "none": None,
            "array": np.array([1.0, 2.0, 3.0]),
            "list": [1, 2, 3],
            "nested_dict": {
                "inner": "value",
                "inner_list": [4, 5, 6],
                "inner_array": np.array([[1, 2], [3, 4]]),
            },
            "list_of_dicts": [
                {"a": 1, "b": np.array([1.0])},
                {"c": 2, "d": [True, False]},
            ],
            "empty_list": [],
            "empty_dict": {},
        }
        self.assertTrue(is_datatree_compatible(valid_data))

    def test_invalid_dict_keys(self):
        """Test that dicts with non-string keys are not compatible."""
        self.assertFalse(is_datatree_compatible({1: "value"}))
        self.assertFalse(is_datatree_compatible({(1, 2): "value"}))
        self.assertFalse(is_datatree_compatible({None: "value"}))

    def test_invalid_types(self):
        """Test that incompatible types return False."""
        self.assertFalse(is_datatree_compatible(object()))
        self.assertFalse(is_datatree_compatible(lambda x: x))
        self.assertFalse(is_datatree_compatible({1, 2, 3}))
        self.assertFalse(is_datatree_compatible((1, 2, 3)))  # tuples not allowed

    def test_invalid_nested_types(self):
        """Test that incompatible types in nested structures return False."""
        self.assertFalse(is_datatree_compatible([1, 2, object()]))
        self.assertFalse(is_datatree_compatible({"key": object()}))
        self.assertFalse(is_datatree_compatible({"key": [1, 2, {3, 4}]}))
        self.assertFalse(is_datatree_compatible({"outer": {"inner": (1, 2, 3)}}))
