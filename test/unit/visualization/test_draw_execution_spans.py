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

"""Unit tests for the visualization folder."""

import random
from datetime import datetime, timedelta

import ddt

from qiskit_ibm_runtime.execution_span import ExecutionSpans, SliceSpan
from qiskit_ibm_runtime.visualization import draw_execution_spans

from ...ibm_test_case import IBMVisualizationTestCase


def execution_spans(seed: int = 100) -> tuple[ExecutionSpans, ExecutionSpans]:
    """Return two sets of spans of pseudo-random duration, one of 100 spans and one of 50.

    Args:
        seed: the seed of the local random generator, to keep the durations reproducible.
    """
    rng = random.Random(seed)

    time0 = time1 = datetime(year=1995, month=7, day=30)
    time1 += timedelta(seconds=30)
    spans0 = []
    spans1 = []
    for idx in range(100):
        delta = timedelta(seconds=4 + 2 * rng.random())
        spans0.append(SliceSpan(time0, time0 := time0 + delta, {0: ((100,), slice(idx, idx + 1))}))

        if idx < 50:
            delta = timedelta(seconds=3 + 3 * rng.random())
            spans1.append(
                SliceSpan(time1, time1 := time1 + delta, {0: ((50,), slice(idx, idx + 1))})
            )

    return ExecutionSpans(spans0), ExecutionSpans(spans1)


def spans_to_draw():
    """Return a set of two spans, the second one starting before the first one ends."""
    span1 = SliceSpan(
        datetime(2023, 8, 22, 18, 45, 3),
        datetime(2023, 8, 22, 18, 45, 10),
        {1: ((100,), slice(4, 9)), 0: ((2, 5), slice(5, 7))},
    )
    span2 = SliceSpan(
        datetime(2023, 8, 22, 18, 45, 9),
        datetime(2023, 8, 22, 18, 45, 11, 500000),
        {0: ((100,), slice(2, 3)), 2: ((32, 3), slice(6, 8))},
    )
    return ExecutionSpans([span2, span1])


@ddt.ddt
class TestExecutionSpans(IBMVisualizationTestCase):
    """Class for testing the draw method of ExecutionSpans."""

    @ddt.data((False, 4, None), (True, 6, "alpha"))
    @ddt.unpack
    def test_draw(self, normalize_y, width, name):
        """Test the draw method."""
        spans = spans_to_draw()
        self.save_plotly_artifact(spans.draw(normalize_y=normalize_y, line_width=width, name=name))


@ddt.ddt
class TestDrawExecutionSpans(IBMVisualizationTestCase):
    """Tests for the ``draw_execution_spans`` function."""

    @ddt.data(False, True)
    def test_one_spans(self, normalize_y):
        """Test with one set of spans."""
        spans0, _ = execution_spans()
        fig = draw_execution_spans(spans0, normalize_y=normalize_y)
        self.save_plotly_artifact(fig)

    @ddt.data(
        (False, False, 4, None), (True, True, 8, "alpha"), (True, False, 4, ["alpha", "beta"])
    )
    @ddt.unpack
    def test_two_spans(self, normalize_y, common_start, width, names):
        """Test with two sets of spans."""
        spans0, spans1 = execution_spans()
        fig = draw_execution_spans(
            spans0,
            spans1,
            normalize_y=normalize_y,
            common_start=common_start,
            line_width=width,
            names=names,
        )
        self.save_plotly_artifact(fig)
