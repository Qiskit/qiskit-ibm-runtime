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

"""Tests ExecutionSpan and ExecutionSpanSet classes."""


from datetime import datetime

from qiskit_ibm_runtime.execution_span import ExecutionSpan, ExecutionSpanSet


from ..ibm_test_case import IBMTestCase


class TestExecutionSpan(IBMTestCase):
    """Class for testing the ExecutionSpan class."""

    def test_to_tuple_from_tuple(self):
        start = datetime(2022, 1, 1)
        stop = datetime(2023, 1, 1)
        data_slices = {1: (4, 9), 0: (5, 7)}

        tuple_expected = (start, stop, data_slices)
        span_expected = ExecutionSpan(start, stop, data_slices)

        span_created = ExecutionSpan.from_tuple(tuple_expected)
        self.assertEqual(span_expected, span_created)

        tuple_created = span_created.to_tuple()
        self.assertEqual(tuple_expected, tuple_created)


class TestExecutionSpanSet(IBMTestCase):
    """Class for testing the ExecutionSpanSet class."""

    def test_str(self):
        start1 = datetime(2022, 1, 1)
        stop1 = datetime(2023, 1, 1)
        slices1 = {1: (4, 9), 0: (5, 7)}
        start2 = datetime(2024, 8, 20)
        stop2 = datetime(2024, 8, 21)
        slices2 = {0: (2, 3)}

        str_expected = str([(start1, stop1, slices1), (start2, stop2, slices2)])

        exec_spans = ExecutionSpanSet.from_list_of_tuple(
            [(start1, stop1, slices1), (start2, stop2, slices2)]
        )
        str_created = str(exec_spans)
        self.assertEqual(str_expected, str_created)
