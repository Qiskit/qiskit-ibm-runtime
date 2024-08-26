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
import ddt

from qiskit_ibm_runtime.execution_span import ExecutionSpan, ExecutionSpanSet

from ..ibm_test_case import IBMTestCase


@ddt.ddt
class TestExecutionSpan(IBMTestCase):
    """Class for testing the ExecutionSpan and ExecutionSpanSet classes."""

    def setUp(self) -> None:
        super().setUp()
        self.start1 = datetime(2023, 8, 22, 18, 45, 3)
        self.stop1 = datetime(2023, 8, 22, 18, 45, 10)
        self.slices1 = {1: slice(4, 9), 0: slice(5, 7)}
        self.span1 = ExecutionSpan(self.start1, self.stop1, self.slices1)

        self.start2 = datetime(2023, 8, 22, 18, 45, 9)
        self.stop2 = datetime(2023, 8, 22, 18, 45, 11, 500000)
        self.slices2 = {0: slice(2, 3), 2: slice(6, 8)}
        self.span2 = ExecutionSpan(self.start2, self.stop2, self.slices2)

        self.span_set = ExecutionSpanSet([self.span1, self.span2])

    def test_duration(self):
        """Test the duration property"""
        duration1 = self.span1.duration
        duration2 = self.span2.duration
        duration_set = self.span_set.duration

        self.assertEqual(duration1, 7)
        self.assertEqual(duration2, 2.5)
        self.assertEqual(duration_set, 8.5)

    @ddt.data(
        (0, True, True),
        ([0, 1], True, True),
        ([0, 1, 2], True, True),
        ([1, 2], True, True),
        ([1], True, False),
        (2, False, True),
        ([0, 2], True, True),
    )
    @ddt.unpack
    def test_contains_pub(self, idx, span1_expected_res, span2_expected_res):
        """The the contains_pub method"""
        self.assertEqual(self.span1.contains_pub(idx), span1_expected_res)
        self.assertEqual(self.span2.contains_pub(idx), span2_expected_res)

    def test_filter_by_pub(self):
        """The the filter_by_pub method"""
        self.assertEqual(self.span1.filter_by_pub([]), ExecutionSpan(self.start1, self.stop1, {}))
        self.assertEqual(self.span2.filter_by_pub([]), ExecutionSpan(self.start2, self.stop2, {}))
        self.assertEqual(
            self.span_set.filter_by_pub([]),
            ExecutionSpanSet(
                [
                    ExecutionSpan(self.start1, self.stop1, {}),
                    ExecutionSpan(self.start2, self.stop2, {}),
                ]
            ),
        )

        self.assertEqual(
            self.span1.filter_by_pub([2, 0]),
            ExecutionSpan(self.start1, self.stop1, {0: self.slices1[0]}),
        )
        self.assertEqual(self.span2.filter_by_pub([2, 0]), self.span2)
        self.assertEqual(
            self.span_set.filter_by_pub([2, 0]),
            ExecutionSpanSet(
                [ExecutionSpan(self.start1, self.stop1, {0: self.slices1[0]}), self.span2]
            ),
        )

        self.assertEqual(
            self.span1.filter_by_pub(1),
            ExecutionSpan(self.start1, self.stop1, {1: self.slices1[1]}),
        )
        self.assertEqual(self.span2.filter_by_pub(1), ExecutionSpan(self.start2, self.stop2, {}))
        self.assertEqual(
            self.span_set.filter_by_pub(1),
            ExecutionSpanSet(
                [
                    ExecutionSpan(self.start1, self.stop1, {1: self.slices1[1]}),
                    ExecutionSpan(self.start2, self.stop2, {}),
                ]
            ),
        )

    def test_sequence_methods(self):
        """Test __len__ and __get_item__"""
        self.assertEqual(len(self.span_set), 2)
        self.assertEqual(self.span_set[0], self.span1)
        self.assertEqual(self.span_set[1], self.span2)
        self.assertEqual(self.span_set[1, 0], ExecutionSpanSet([self.span2, self.span1]))
