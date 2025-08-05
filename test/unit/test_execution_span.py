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

"""Tests SliceSpan and ExecutionSpans classes."""


from datetime import datetime, timedelta
import ddt

import numpy as np
import numpy.testing as npt
from qiskit_ibm_runtime.execution_span import (
    SliceSpan,
    DoubleSliceSpan,
    ExecutionSpans,
    TwirledSliceSpan,
    TwirledSliceSpanV2,
)

from ..ibm_test_case import IBMTestCase


@ddt.ddt
class TestSliceSpan(IBMTestCase):
    """Class for testing SliceSpan."""

    def setUp(self) -> None:
        super().setUp()
        self.start1 = datetime(2023, 8, 22, 18, 45, 3)
        self.stop1 = datetime(2023, 8, 22, 18, 45, 10)
        self.slices1 = {1: ((100,), slice(4, 9)), 0: ((5, 2), slice(5, 7))}
        self.span1 = SliceSpan(self.start1, self.stop1, self.slices1)

        self.start2 = datetime(2023, 8, 22, 18, 45, 9)
        self.stop2 = datetime(2023, 8, 22, 18, 45, 11, 500000)
        self.slices2 = {0: ((100,), slice(2, 3)), 2: ((32, 3), slice(6, 8))}
        self.span2 = SliceSpan(self.start2, self.stop2, self.slices2)

    def test_limits(self):
        """Test the start and stop properties"""
        self.assertEqual(self.span1.start, self.start1)
        self.assertEqual(self.span1.stop, self.stop1)
        self.assertEqual(self.span2.start, self.start2)
        self.assertEqual(self.span2.stop, self.stop2)

    def test_equality(self):
        """Test the equality method."""
        self.assertEqual(self.span1, self.span1)
        self.assertEqual(self.span1, SliceSpan(self.start1, self.stop1, self.slices1))
        self.assertNotEqual(self.span1, self.span2)
        self.assertNotEqual(self.span1, "aoeu")

    def test_comparison(self):
        """Test the comparison method."""
        self.assertLess(self.span1, self.span2)

        dt = timedelta(seconds=1)
        span1_plus = SliceSpan(self.start1, self.stop1 + dt, self.slices1)
        self.assertLess(self.span1, span1_plus)

        span1_minus = SliceSpan(self.start1, self.stop1 - dt, self.slices1)
        self.assertGreater(self.span1, span1_minus)

    def test_duration(self):
        """Test the duration property"""
        self.assertEqual(self.span1.duration, 7)
        self.assertEqual(self.span2.duration, 2.5)

    def test_repr(self):
        """Test the repr method"""
        expect = "start='2023-08-22 18:45:03', stop='2023-08-22 18:45:10', size=7"
        self.assertEqual(repr(self.span1), f"SliceSpan(<{expect}>)")

    def test_size(self):
        """Test the size property"""
        self.assertEqual(self.span1.size, 5 + 2)
        self.assertEqual(self.span2.size, 1 + 2)

    def test_pub_idxs(self):
        """Test the pub_idxs property"""
        self.assertEqual(self.span1.pub_idxs, [0, 1])
        self.assertEqual(self.span2.pub_idxs, [0, 2])

    def test_mask(self):
        """Test the mask() method"""
        mask1 = np.zeros((100,), dtype=bool)
        mask1[4:9] = True
        npt.assert_array_equal(self.span1.mask(1), mask1)

        mask2 = [[0, 0], [0, 0], [0, 1], [1, 0], [0, 0]]
        npt.assert_array_equal(self.span1.mask(0), np.array(mask2, dtype=bool))

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
        self.assertEqual(self.span1.filter_by_pub([]), SliceSpan(self.start1, self.stop1, {}))
        self.assertEqual(self.span2.filter_by_pub([]), SliceSpan(self.start2, self.stop2, {}))

        self.assertEqual(
            self.span1.filter_by_pub([2, 0]),
            SliceSpan(self.start1, self.stop1, {0: self.slices1[0]}),
        )
        self.assertEqual(self.span2.filter_by_pub([2, 0]), self.span2)

        self.assertEqual(
            self.span1.filter_by_pub(1),
            SliceSpan(self.start1, self.stop1, {1: self.slices1[1]}),
        )
        self.assertEqual(self.span2.filter_by_pub(1), SliceSpan(self.start2, self.stop2, {}))


@ddt.ddt
class TestDoubleSliceSpan(IBMTestCase):
    """Class for testing DoubleSliceSpan."""

    def setUp(self) -> None:
        super().setUp()
        self.start1 = datetime(2024, 10, 11, 4, 31, 30)
        self.stop1 = datetime(2024, 10, 11, 4, 31, 34)
        self.slices1 = {
            2: ((1, 100), slice(1), slice(4, 9)),
            0: ((3, 5, 10), slice(10, 13), slice(2, 5)),
        }
        self.span1 = DoubleSliceSpan(self.start1, self.stop1, self.slices1)

        self.start2 = datetime(2024, 10, 16, 11, 9, 20)
        self.stop2 = datetime(2024, 10, 16, 11, 9, 30)
        self.slices2 = {
            0: ((5, 100), slice(3, 5), slice(20, 40)),
            1: ((1, 5, 3), slice(2, 5), slice(3)),
        }
        self.span2 = DoubleSliceSpan(self.start2, self.stop2, self.slices2)

    def test_limits(self):
        """Test the start and stop properties"""
        self.assertEqual(self.span1.start, self.start1)
        self.assertEqual(self.span1.stop, self.stop1)
        self.assertEqual(self.span2.start, self.start2)
        self.assertEqual(self.span2.stop, self.stop2)

    def test_equality(self):
        """Test the equality method."""
        self.assertEqual(self.span1, self.span1)
        self.assertEqual(self.span1, DoubleSliceSpan(self.start1, self.stop1, self.slices1))
        self.assertNotEqual(self.span1, "aoeu")
        self.assertNotEqual(self.span1, self.span2)

    def test_duration(self):
        """Test the duration property"""
        self.assertEqual(self.span1.duration, 4)
        self.assertEqual(self.span2.duration, 10)

    def test_repr(self):
        """Test the repr method"""
        expect = "start='2024-10-11 04:31:30', stop='2024-10-11 04:31:34', size=14"
        self.assertEqual(repr(self.span1), f"DoubleSliceSpan(<{expect}>)")

    def test_size(self):
        """Test the size property"""
        self.assertEqual(self.span1.size, 1 * 5 + 3 * 3)
        self.assertEqual(self.span2.size, 2 * 20 + 3 * 3)

    def test_pub_idxs(self):
        """Test the pub_idxs property"""
        self.assertEqual(self.span1.pub_idxs, [0, 2])
        self.assertEqual(self.span2.pub_idxs, [0, 1])

    def test_mask(self):
        """Test the mask() method"""
        mask1 = np.zeros((1, 100), dtype=bool)
        mask1[0][4:9] = True
        npt.assert_array_equal(self.span1.mask(2), mask1)

        mask2 = [[[0, 0, 0], [0, 0, 0], [1, 1, 1], [1, 1, 1], [1, 1, 1]]]
        npt.assert_array_equal(self.span2.mask(1), mask2)

    @ddt.data(
        (0, True, True),
        ([0, 1], True, True),
        ([0, 1, 2], True, True),
        ([1, 2], True, True),
        ([1], False, True),
        (2, True, False),
        ([0, 2], True, True),
    )
    @ddt.unpack
    def test_contains_pub(self, idx, span1_expected_res, span2_expected_res):
        """The the contains_pub method"""
        self.assertEqual(self.span1.contains_pub(idx), span1_expected_res)
        self.assertEqual(self.span2.contains_pub(idx), span2_expected_res)

    def test_filter_by_pub(self):
        """The the filter_by_pub method"""
        self.assertEqual(self.span1.filter_by_pub([]), DoubleSliceSpan(self.start1, self.stop1, {}))
        self.assertEqual(self.span2.filter_by_pub([]), DoubleSliceSpan(self.start2, self.stop2, {}))

        self.assertEqual(
            self.span1.filter_by_pub([1, 0]),
            DoubleSliceSpan(self.start1, self.stop1, {0: self.slices1[0]}),
        )

        self.assertEqual(
            self.span1.filter_by_pub(2),
            DoubleSliceSpan(self.start1, self.stop1, {2: self.slices1[2]}),
        )

    def test_one_dimensional_shape_mask(self):
        """Test that mask doesn't throw with a one-dimensional shape"""
        span = DoubleSliceSpan(self.start1, self.stop1, {0: ((7,), slice(0, 1), slice(0, 7))})

        span.mask(0)


@ddt.ddt
class TestTwirledSliceSpan(IBMTestCase):
    """Class for testing TwirledSliceSpan."""

    def setUp(self) -> None:
        super().setUp()
        self.start1 = datetime(2024, 10, 11, 4, 31, 30)
        self.stop1 = datetime(2024, 10, 11, 4, 31, 34)
        self.slices1 = {
            2: ((3, 1, 5), True, slice(1), slice(2, 4)),
            0: ((3, 5, 18, 10), False, slice(10, 13), slice(2, 5)),
        }
        self.span1 = TwirledSliceSpan(self.start1, self.stop1, self.slices1)

        self.start2 = datetime(2024, 10, 16, 11, 9, 20)
        self.stop2 = datetime(2024, 10, 16, 11, 9, 30)
        self.slices2 = {
            0: ((7, 5, 100), True, slice(3, 5), slice(20, 40)),
            1: ((1, 5, 2, 3), False, slice(3, 9), slice(1, 3)),
        }
        self.span2 = TwirledSliceSpan(self.start2, self.stop2, self.slices2)

        self.start3 = self.start1
        self.stop3 = self.stop1
        # reducing for pub 2 from 15 to 4 shots
        self.slices3 = {0: self.slices1[0] + (180,), 2: self.slices1[2] + (4,)}
        self.span3 = TwirledSliceSpanV2(self.start3, self.stop3, self.slices3)

    def test_limits(self):
        """Test the start and stop properties"""
        self.assertEqual(self.span1.start, self.start1)
        self.assertEqual(self.span1.stop, self.stop1)
        self.assertEqual(self.span2.start, self.start2)
        self.assertEqual(self.span2.stop, self.stop2)

    def test_equality(self):
        """Test the equality method."""
        self.assertEqual(self.span1, self.span1)
        self.assertEqual(self.span1, TwirledSliceSpan(self.start1, self.stop1, self.slices1))
        self.assertNotEqual(self.span1, "aoeu")
        self.assertNotEqual(self.span1, self.span2)

    def test_duration(self):
        """Test the duration property"""
        self.assertEqual(self.span1.duration, 4)
        self.assertEqual(self.span2.duration, 10)

    def test_repr(self):
        """Test the repr method"""
        expect = "start='2024-10-11 04:31:30', stop='2024-10-11 04:31:34', size=11"
        self.assertEqual(repr(self.span1), f"TwirledSliceSpan(<{expect}>)")

    def test_size(self):
        """Test the size property"""
        self.assertEqual(self.span1.size, 1 * 2 + 3 * 3)
        self.assertEqual(self.span2.size, 2 * 20 + 6 * 2)

    def test_pub_idxs(self):
        """Test the pub_idxs property"""
        self.assertEqual(self.span1.pub_idxs, [0, 2])
        self.assertEqual(self.span2.pub_idxs, [0, 1])

    def test_mask(self):
        """Test the mask() method"""
        # reminder: ((3, 1, 5), True, slice(1), slice(2, 4))
        mask1 = np.zeros((3, 1, 5), dtype=bool)
        mask1.reshape((3, 5))[:1, 2:4] = True
        mask1 = mask1.transpose((1, 0, 2)).reshape((1, 15))
        npt.assert_array_equal(self.span1.mask(2), mask1)

        # reminder: ((1, 5, 2, 3), False, slice(3,9), slice(1, 3)),
        mask2 = [
            [
                [[[0, 0, 0], [0, 0, 0]]],
                [[[0, 0, 0], [0, 1, 1]]],
                [[[0, 1, 1], [0, 1, 1]]],
                [[[0, 1, 1], [0, 1, 1]]],
                [[[0, 1, 1], [0, 0, 0]]],
            ]
        ]
        mask2 = np.array(mask2, dtype=bool).reshape((1, 5, 6))
        npt.assert_array_equal(self.span2.mask(1), mask2)

        mask3 = [[False, False, True, True]]
        npt.assert_array_equal(self.span3.mask(2), mask3)

        with self.assertRaisesRegex(KeyError, "Pub 1 is not included in the span."):
            self.span1.mask(1)

    @ddt.data(
        (0, True, True),
        ([0, 1], True, True),
        ([0, 1, 2], True, True),
        ([1, 2], True, True),
        ([1], False, True),
        (2, True, False),
        ([0, 2], True, True),
    )
    @ddt.unpack
    def test_contains_pub(self, idx, span1_expected_res, span2_expected_res):
        """The the contains_pub method"""
        self.assertEqual(self.span1.contains_pub(idx), span1_expected_res)
        self.assertEqual(self.span2.contains_pub(idx), span2_expected_res)

    def test_filter_by_pub(self):
        """The the filter_by_pub method"""
        self.assertEqual(
            self.span1.filter_by_pub([]), TwirledSliceSpan(self.start1, self.stop1, {})
        )
        self.assertEqual(
            self.span2.filter_by_pub([]), TwirledSliceSpan(self.start2, self.stop2, {})
        )

        self.assertEqual(
            self.span1.filter_by_pub([1, 0]),
            TwirledSliceSpan(self.start1, self.stop1, {0: self.slices1[0]}),
        )

        self.assertEqual(
            self.span1.filter_by_pub(2),
            TwirledSliceSpan(self.start1, self.stop1, {2: self.slices1[2]}),
        )

    def test_one_dimensional_shape_mask(self):
        """Test that mask doesn't throw with a one-dimensional shape"""
        span = TwirledSliceSpan(
            self.start1, self.stop1, {0: ((7,), False, slice(0, 1), slice(0, 7))}
        )
        span.mask(0)


@ddt.ddt
class TestExecutionSpans(IBMTestCase):
    """Class for testing ExecutionSpans."""

    def setUp(self) -> None:
        super().setUp()
        self.start1 = datetime(2023, 8, 22, 18, 45, 3)
        self.stop1 = datetime(2023, 8, 22, 18, 45, 10)
        self.slices1 = {1: ((100,), slice(4, 9)), 0: ((2, 5), slice(5, 7))}
        self.span1 = SliceSpan(self.start1, self.stop1, self.slices1)

        self.start2 = datetime(2023, 8, 22, 18, 45, 9)
        self.stop2 = datetime(2023, 8, 22, 18, 45, 11, 500000)
        self.slices2 = {0: ((100,), slice(2, 3)), 2: ((32, 3), slice(6, 8))}
        self.span2 = SliceSpan(self.start2, self.stop2, self.slices2)

        self.spans = ExecutionSpans([self.span1, self.span2])

    def test_duration(self):
        """Test the duration property"""
        self.assertEqual(self.spans.duration, 8.5)

    def test_filter_by_pub(self):
        """The the filter_by_pub method"""
        self.assertEqual(
            self.spans.filter_by_pub([]),
            ExecutionSpans(
                [
                    SliceSpan(self.start1, self.stop1, {}),
                    SliceSpan(self.start2, self.stop2, {}),
                ]
            ),
        )

        self.assertEqual(
            self.spans.filter_by_pub([2, 0]),
            ExecutionSpans([SliceSpan(self.start1, self.stop1, {0: self.slices1[0]}), self.span2]),
        )

        self.assertEqual(
            self.spans.filter_by_pub(1),
            ExecutionSpans(
                [
                    SliceSpan(self.start1, self.stop1, {1: self.slices1[1]}),
                    SliceSpan(self.start2, self.stop2, {}),
                ]
            ),
        )

    def test_sequence_methods(self):
        """Test __len__ and __get_item__"""
        self.assertEqual(len(self.spans), 2)
        self.assertEqual(self.spans[0], self.span1)
        self.assertEqual(self.spans[1], self.span2)
        self.assertEqual(self.spans[1, 0], ExecutionSpans([self.span2, self.span1]))

    def test_sort(self):
        """Test the sort method."""
        spans = ExecutionSpans([self.span2, self.span1])
        self.assertLess(spans[1], spans[0])
        inplace_sort = spans.sort()
        self.assertIs(inplace_sort, spans)
        self.assertLess(spans[0], spans[1])

        spans = ExecutionSpans([self.span2, self.span1])
        new_sort = spans.sort(inplace=False)
        self.assertIsNot(inplace_sort, spans)
        self.assertLess(spans[1], spans[0])
        self.assertLess(new_sort[0], new_sort[1])

    @ddt.data((False, 4, None), (True, 6, "alpha"))
    @ddt.unpack
    def test_draw(self, normalize_y, width, name):
        """Test the draw method."""
        spans = ExecutionSpans([self.span2, self.span1])
        self.save_plotly_artifact(spans.draw(normalize_y=normalize_y, line_width=width, name=name))
