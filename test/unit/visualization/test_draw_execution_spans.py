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

import pytest

from qiskit_ibm_runtime.execution_span import ExecutionSpans, SliceSpan
from qiskit_ibm_runtime.visualization import draw_execution_spans

from .utils import save_plotly_artifact


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


@pytest.fixture
def spans_to_draw() -> ExecutionSpans:
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


class TestExecutionSpans:
    """Class for testing the draw method of ExecutionSpans."""

    @pytest.mark.parametrize(
        ("normalize_y", "width", "name"), [(False, 4, None), (True, 6, "alpha")]
    )
    def test_draw(
        self,
        normalize_y: bool,
        width: int,
        name: str | None,
        spans_to_draw: ExecutionSpans,
        test_id: str,
    ) -> None:
        """Test the draw method."""
        save_plotly_artifact(
            test_id, spans_to_draw.draw(normalize_y=normalize_y, line_width=width, name=name)
        )


class TestDrawExecutionSpans:
    """Tests for the ``draw_execution_spans`` function."""

    @pytest.mark.parametrize("normalize_y", [False, True])
    def test_one_spans(self, normalize_y: bool, test_id: str) -> None:
        """Test with one set of spans."""
        spans0, _ = execution_spans()
        fig = draw_execution_spans(spans0, normalize_y=normalize_y)
        save_plotly_artifact(test_id, fig)

    @pytest.mark.parametrize(
        ("normalize_y", "common_start", "width", "names"),
        [(False, False, 4, None), (True, True, 8, "alpha"), (True, False, 4, ["alpha", "beta"])],
    )
    def test_two_spans(
        self,
        normalize_y: bool,
        common_start: bool,
        width: int,
        names: str | list[str] | None,
        test_id: str,
    ) -> None:
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
        save_plotly_artifact(test_id, fig)
