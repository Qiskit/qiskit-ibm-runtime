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

"""Unit tests for the visualization folder."""


from datetime import datetime, timedelta
import random

import ddt

from qiskit_ibm_runtime.execution_span import ExecutionSpans, SliceSpan
from qiskit_ibm_runtime.visualization import draw_execution_spans

from ...ibm_test_case import IBMTestCase


@ddt.ddt
class TestDrawExecutionSpans(IBMTestCase):
    """Tests for the ``draw_execution_spans`` function."""

    def setUp(self) -> None:
        """Set up."""
        random.seed(100)

        time0 = time1 = datetime(year=1995, month=7, day=30)
        time1 += timedelta(seconds=30)
        spans0 = []
        spans1 = []
        for idx in range(100):
            delta = timedelta(seconds=4 + 2 * random.random())
            spans0.append(
                SliceSpan(time0, time0 := time0 + delta, {0: ((100,), slice(idx, idx + 1))})
            )

            if idx < 50:
                delta = timedelta(seconds=3 + 3 * random.random())
                spans1.append(
                    SliceSpan(time1, time1 := time1 + delta, {0: ((50,), slice(idx, idx + 1))})
                )

        self.spans0 = ExecutionSpans(spans0)
        self.spans1 = ExecutionSpans(spans1)

    @ddt.data(False, True)
    def test_one_spans(self, normalize_y):
        """Test with one set of spans."""
        fig = draw_execution_spans(self.spans0, normalize_y=normalize_y)
        self.save_plotly_artifact(fig)

    @ddt.data(
        (False, False, 4, None), (True, True, 8, "alpha"), (True, False, 4, ["alpha", "beta"])
    )
    @ddt.unpack
    def test_two_spans(self, normalize_y, common_start, width, names):
        """Test with two sets of spans."""
        fig = draw_execution_spans(
            self.spans0,
            self.spans1,
            normalize_y=normalize_y,
            common_start=common_start,
            line_width=width,
            names=names,
        )
        self.save_plotly_artifact(fig)
