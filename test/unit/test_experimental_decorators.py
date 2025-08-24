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

"""Tests for the functions in ``utils.deprecation``."""

from __future__ import annotations
import unittest
import warnings

from qiskit_ibm_runtime.utils.experimental import experimental_arg, experimental_func
from qiskit_ibm_runtime.exceptions import IBMRuntimeExperimentalWarning

from ..ibm_test_case import IBMTestCase


class TestExperimentalDecorators(IBMTestCase):

    def test_experimental_class(self):
        @experimental_func(since="0.41.0")
        class ExperimentalClass:
            def __init__(self):
                self.value = 42

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            obj = ExperimentalClass()
            self.assertEqual(obj.value, 42)
            self.assertEqual(len(w), 1)
            self.assertTrue(issubclass(w[0].category, IBMRuntimeExperimentalWarning))
            self.assertIn("class", str(w[0].message))

    def test_experimental_method(self):
        class MyClass:
            @experimental_func(since="0.42.0")
            def experimental_method(self):
                return "method called"

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = MyClass().experimental_method()
            self.assertEqual(result, "method called")
            self.assertEqual(len(w), 1)
            self.assertTrue(issubclass(w[0].category, IBMRuntimeExperimentalWarning))
            self.assertIn("method", str(w[0].message))

    def test_experimental_property(self):
        class MyClass:
            @property
            @experimental_func(since="0.43.0", is_property=True)
            def experimental_property(self):
                return "property value"

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = MyClass().experimental_property
            self.assertEqual(result, "property value")
            self.assertEqual(len(w), 1)
            self.assertTrue(issubclass(w[0].category, IBMRuntimeExperimentalWarning))
            self.assertIn("property", str(w[0].message))

    def test_experimental_argument(self):
        @experimental_arg("x", since="0.44.0")
        def my_function(x=None):
            return x

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = my_function(x=123)
            self.assertEqual(result, 123)
            self.assertEqual(len(w), 1)
            self.assertTrue(issubclass(w[0].category, IBMRuntimeExperimentalWarning))
            self.assertIn("argument", str(w[0].message))


if __name__ == "__main__":
    unittest.main()
