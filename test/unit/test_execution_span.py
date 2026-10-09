# This code is part of Qiskit.
#
# (C) Copyright IBM 2024-2026.
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
    DoubleSliceSpan,
    ExecutionSpans,
    SliceSpan,
    TwirledSliceSpan,
    TwirledSliceSpanV2,
)

from ..ibm_test_case import IBMTestCase


def slice_spans():
    """Return two slice spans, and the data slices of the first one."""
    slices1 = {1: ((100,), slice(4, 9)), 0: ((5, 2), slice(5, 7))}

    span1 = SliceSpan(
        datetime(2023, 8, 22, 18, 45, 3),
        datetime(2023, 8, 22, 18, 45, 10),
        slices1,
    )
    span2 = SliceSpan(
        datetime(2023, 8, 22, 18, 45, 9),
        datetime(2023, 8, 22, 18, 45, 11, 500000),
        {0: ((100,), slice(2, 3)), 2: ((32, 3), slice(6, 8))},
    )

    return span1, span2, slices1


def double_slice_spans():
    """Return two double slice spans, and the data slices of the first one."""
    slices1 = {
        2: ((1, 100), slice(1), slice(4, 9)),
        0: ((3, 5, 10), slice(10, 13), slice(2, 5)),
    }

    span1 = DoubleSliceSpan(
        datetime(2024, 10, 11, 4, 31, 30),
        datetime(2024, 10, 11, 4, 31, 34),
        slices1,
    )
    span2 = DoubleSliceSpan(
        datetime(2024, 10, 16, 11, 9, 20),
        datetime(2024, 10, 16, 11, 9, 30),
        {
            0: ((5, 100), slice(3, 5), slice(20, 40)),
            1: ((1, 5, 3), slice(2, 5), slice(3)),
        },
    )

    return span1, span2, slices1


def twirled_slice_spans():
    """Return two twirled slice spans, a version 2 one, and the data slices of the first one."""
    slices1 = {
        2: ((3, 1, 5), True, slice(1), slice(2, 4)),
        0: ((3, 5, 18, 10), False, slice(10, 13), slice(2, 5)),
    }

    span1 = TwirledSliceSpan(
        datetime(2024, 10, 11, 4, 31, 30),
        datetime(2024, 10, 11, 4, 31, 34),
        slices1,
    )
    span2 = TwirledSliceSpan(
        datetime(2024, 10, 16, 11, 9, 20),
        datetime(2024, 10, 16, 11, 9, 30),
        {
            0: ((7, 5, 100), True, slice(3, 5), slice(20, 40)),
            1: ((1, 5, 2, 3), False, slice(3, 9), slice(1, 3)),
        },
    )
    # same window as the first span, reducing for pub 2 from 15 to 4 shots
    span3 = TwirledSliceSpanV2(
        span1.start,
        span1.stop,
        {0: slices1[0] + (180,), 2: slices1[2] + (4,)},
    )

    return span1, span2, span3, slices1


def execution_spans():
    """Return a set of two slice spans, the spans themselves, and the slices of the first one."""
    slices1 = {1: ((100,), slice(4, 9)), 0: ((2, 5), slice(5, 7))}

    span1 = SliceSpan(
        datetime(2023, 8, 22, 18, 45, 3),
        datetime(2023, 8, 22, 18, 45, 10),
        slices1,
    )
    span2 = SliceSpan(
        datetime(2023, 8, 22, 18, 45, 9),
        datetime(2023, 8, 22, 18, 45, 11, 500000),
        {0: ((100,), slice(2, 3)), 2: ((32, 3), slice(6, 8))},
    )

    return ExecutionSpans([span1, span2]), span1, span2, slices1


@ddt.ddt
class TestSliceSpan(IBMTestCase):
    """Class for testing SliceSpan."""

    def test_limits(self):
        """Test the start and stop properties."""
        span1, span2, _ = slice_spans()

        assert span1.start == datetime(2023, 8, 22, 18, 45, 3)
        assert span1.stop == datetime(2023, 8, 22, 18, 45, 10)
        assert span2.start == datetime(2023, 8, 22, 18, 45, 9)
        assert span2.stop == datetime(2023, 8, 22, 18, 45, 11, 500000)

    def test_equality(self):
        """Test the equality method."""
        span1, span2, slices1 = slice_spans()

        assert span1 == span1
        assert span1 == SliceSpan(span1.start, span1.stop, slices1)
        assert span1 != span2
        assert span1 != "aoeu"

    def test_comparison(self):
        """Test the comparison method."""
        span1, span2, slices1 = slice_spans()

        assert span1 < span2

        dt = timedelta(seconds=1)
        span1_plus = SliceSpan(span1.start, span1.stop + dt, slices1)
        assert span1 < span1_plus

        span1_minus = SliceSpan(span1.start, span1.stop - dt, slices1)
        assert span1 > span1_minus

    def test_duration(self):
        """Test the duration property."""
        span1, span2, _ = slice_spans()

        assert span1.duration == 7
        assert span2.duration == 2.5

    def test_repr(self):
        """Test the repr method."""
        span1, _, _ = slice_spans()

        expect = "start='2023-08-22 18:45:03', stop='2023-08-22 18:45:10', size=7"
        assert repr(span1) == f"SliceSpan(<{expect}>)"

    def test_size(self):
        """Test the size property."""
        span1, span2, _ = slice_spans()

        assert span1.size == 5 + 2
        assert span2.size == 1 + 2

    def test_pub_idxs(self):
        """Test the pub_idxs property."""
        span1, span2, _ = slice_spans()

        assert span1.pub_idxs == [0, 1]
        assert span2.pub_idxs == [0, 2]

    def test_mask(self):
        """Test the mask() method."""
        span1, _, _ = slice_spans()

        mask1 = np.zeros((100,), dtype=bool)
        mask1[4:9] = True
        npt.assert_array_equal(span1.mask(1), mask1)

        mask2 = [[0, 0], [0, 0], [0, 1], [1, 0], [0, 0]]
        npt.assert_array_equal(span1.mask(0), np.array(mask2, dtype=bool))

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
        """Test the contains_pub method."""
        span1, span2, _ = slice_spans()

        assert span1.contains_pub(idx) == span1_expected_res
        assert span2.contains_pub(idx) == span2_expected_res

    def test_filter_by_pub(self):
        """Test the filter_by_pub method."""
        span1, span2, slices1 = slice_spans()

        assert span1.filter_by_pub([]) == SliceSpan(span1.start, span1.stop, {})
        assert span2.filter_by_pub([]) == SliceSpan(span2.start, span2.stop, {})

        assert span1.filter_by_pub([2, 0]) == SliceSpan(span1.start, span1.stop, {0: slices1[0]})
        assert span2.filter_by_pub([2, 0]) == span2

        assert span1.filter_by_pub(1) == SliceSpan(span1.start, span1.stop, {1: slices1[1]})
        assert span2.filter_by_pub(1) == SliceSpan(span2.start, span2.stop, {})


@ddt.ddt
class TestDoubleSliceSpan(IBMTestCase):
    """Class for testing DoubleSliceSpan."""

    def test_limits(self):
        """Test the start and stop properties."""
        span1, span2, _ = double_slice_spans()

        assert span1.start == datetime(2024, 10, 11, 4, 31, 30)
        assert span1.stop == datetime(2024, 10, 11, 4, 31, 34)
        assert span2.start == datetime(2024, 10, 16, 11, 9, 20)
        assert span2.stop == datetime(2024, 10, 16, 11, 9, 30)

    def test_equality(self):
        """Test the equality method."""
        span1, span2, slices1 = double_slice_spans()

        assert span1 == span1
        assert span1 == DoubleSliceSpan(span1.start, span1.stop, slices1)
        assert span1 != "aoeu"
        assert span1 != span2

    def test_duration(self):
        """Test the duration property."""
        span1, span2, _ = double_slice_spans()

        assert span1.duration == 4
        assert span2.duration == 10

    def test_repr(self):
        """Test the repr method."""
        span1, _, _ = double_slice_spans()

        expect = "start='2024-10-11 04:31:30', stop='2024-10-11 04:31:34', size=14"
        assert repr(span1) == f"DoubleSliceSpan(<{expect}>)"

    def test_size(self):
        """Test the size property."""
        span1, span2, _ = double_slice_spans()

        assert span1.size == 1 * 5 + 3 * 3
        assert span2.size == 2 * 20 + 3 * 3

    def test_pub_idxs(self):
        """Test the pub_idxs property."""
        span1, span2, _ = double_slice_spans()

        assert span1.pub_idxs == [0, 2]
        assert span2.pub_idxs == [0, 1]

    def test_mask(self):
        """Test the mask() method."""
        span1, span2, _ = double_slice_spans()

        mask1 = np.zeros((1, 100), dtype=bool)
        mask1[0][4:9] = True
        npt.assert_array_equal(span1.mask(2), mask1)

        mask2 = [[[0, 0, 0], [0, 0, 0], [1, 1, 1], [1, 1, 1], [1, 1, 1]]]
        npt.assert_array_equal(span2.mask(1), mask2)

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
        """Test the contains_pub method."""
        span1, span2, _ = double_slice_spans()

        assert span1.contains_pub(idx) == span1_expected_res
        assert span2.contains_pub(idx) == span2_expected_res

    def test_filter_by_pub(self):
        """Test the filter_by_pub method."""
        span1, span2, slices1 = double_slice_spans()

        assert span1.filter_by_pub([]) == DoubleSliceSpan(span1.start, span1.stop, {})
        assert span2.filter_by_pub([]) == DoubleSliceSpan(span2.start, span2.stop, {})

        assert span1.filter_by_pub([1, 0]) == DoubleSliceSpan(
            span1.start, span1.stop, {0: slices1[0]}
        )

        assert span1.filter_by_pub(2) == DoubleSliceSpan(span1.start, span1.stop, {2: slices1[2]})

    def test_one_dimensional_shape_mask(self):
        """Test that mask doesn't throw with a one-dimensional shape."""
        span1, _, _ = double_slice_spans()

        span = DoubleSliceSpan(span1.start, span1.stop, {0: ((7,), slice(0, 1), slice(0, 7))})

        span.mask(0)


@ddt.ddt
class TestTwirledSliceSpan(IBMTestCase):
    """Class for testing TwirledSliceSpan."""

    def test_limits(self):
        """Test the start and stop properties."""
        span1, span2, _, _ = twirled_slice_spans()

        assert span1.start == datetime(2024, 10, 11, 4, 31, 30)
        assert span1.stop == datetime(2024, 10, 11, 4, 31, 34)
        assert span2.start == datetime(2024, 10, 16, 11, 9, 20)
        assert span2.stop == datetime(2024, 10, 16, 11, 9, 30)

    def test_equality(self):
        """Test the equality method."""
        span1, span2, _, slices1 = twirled_slice_spans()

        assert span1 == span1
        assert span1 == TwirledSliceSpan(span1.start, span1.stop, slices1)
        assert span1 != "aoeu"
        assert span1 != span2

    def test_duration(self):
        """Test the duration property."""
        span1, span2, _, _ = twirled_slice_spans()

        assert span1.duration == 4
        assert span2.duration == 10

    def test_repr(self):
        """Test the repr method."""
        span1, _, _, _ = twirled_slice_spans()

        expect = "start='2024-10-11 04:31:30', stop='2024-10-11 04:31:34', size=11"
        assert repr(span1) == f"TwirledSliceSpan(<{expect}>)"

    def test_size(self):
        """Test the size property."""
        span1, span2, _, _ = twirled_slice_spans()

        assert span1.size == 1 * 2 + 3 * 3
        assert span2.size == 2 * 20 + 6 * 2

    def test_pub_idxs(self):
        """Test the pub_idxs property."""
        span1, span2, _, _ = twirled_slice_spans()

        assert span1.pub_idxs == [0, 2]
        assert span2.pub_idxs == [0, 1]

    def test_mask(self):
        """Test the mask() method."""
        span1, span2, span3, _ = twirled_slice_spans()

        # reminder: ((3, 1, 5), True, slice(1), slice(2, 4))
        mask1 = np.zeros((3, 1, 5), dtype=bool)
        mask1.reshape((3, 5))[:1, 2:4] = True
        mask1 = mask1.transpose((1, 0, 2)).reshape((1, 15))
        npt.assert_array_equal(span1.mask(2), mask1)

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
        npt.assert_array_equal(span2.mask(1), mask2)

        mask3 = [[False, False, True, True]]
        npt.assert_array_equal(span3.mask(2), mask3)

        with self.assertRaisesRegex(KeyError, "Pub 1 is not included in the span."):
            span1.mask(1)

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
        """Test the contains_pub method."""
        span1, span2, _, _ = twirled_slice_spans()

        assert span1.contains_pub(idx) == span1_expected_res
        assert span2.contains_pub(idx) == span2_expected_res

    def test_filter_by_pub(self):
        """Test the filter_by_pub method."""
        span1, span2, _, slices1 = twirled_slice_spans()

        assert span1.filter_by_pub([]) == TwirledSliceSpan(span1.start, span1.stop, {})
        assert span2.filter_by_pub([]) == TwirledSliceSpan(span2.start, span2.stop, {})

        assert span1.filter_by_pub([1, 0]) == TwirledSliceSpan(
            span1.start, span1.stop, {0: slices1[0]}
        )

        assert span1.filter_by_pub(2) == TwirledSliceSpan(span1.start, span1.stop, {2: slices1[2]})

    def test_one_dimensional_shape_mask(self):
        """Test that mask doesn't throw with a one-dimensional shape."""
        span1, _, _, _ = twirled_slice_spans()

        span = TwirledSliceSpan(
            span1.start, span1.stop, {0: ((7,), False, slice(0, 1), slice(0, 7))}
        )
        span.mask(0)


@ddt.ddt
class TestExecutionSpans(IBMTestCase):
    """Class for testing ExecutionSpans."""

    def test_duration(self):
        """Test the duration property."""
        spans, _, _, _ = execution_spans()

        assert spans.duration == 8.5

    def test_filter_by_pub(self):
        """Test the filter_by_pub method."""
        spans, span1, span2, slices1 = execution_spans()

        assert spans.filter_by_pub([]) == ExecutionSpans(
            [
                SliceSpan(span1.start, span1.stop, {}),
                SliceSpan(span2.start, span2.stop, {}),
            ]
        )

        assert spans.filter_by_pub([2, 0]) == ExecutionSpans(
            [SliceSpan(span1.start, span1.stop, {0: slices1[0]}), span2]
        )

        assert spans.filter_by_pub(1) == ExecutionSpans(
            [
                SliceSpan(span1.start, span1.stop, {1: slices1[1]}),
                SliceSpan(span2.start, span2.stop, {}),
            ]
        )

    def test_sequence_methods(self):
        """Test __len__ and __get_item__."""
        spans, span1, span2, _ = execution_spans()

        assert len(spans) == 2
        assert spans[0] == span1
        assert spans[1] == span2
        assert spans[1, 0] == ExecutionSpans([span2, span1])

    def test_sort(self):
        """Test the sort method."""
        _, span1, span2, _ = execution_spans()

        spans = ExecutionSpans([span2, span1])
        assert spans[1] < spans[0]
        inplace_sort = spans.sort()
        assert inplace_sort is spans
        assert spans[0] < spans[1]

        spans = ExecutionSpans([span2, span1])
        new_sort = spans.sort(inplace=False)
        assert inplace_sort is not spans
        assert spans[1] < spans[0]
        assert new_sort[0] < new_sort[1]
