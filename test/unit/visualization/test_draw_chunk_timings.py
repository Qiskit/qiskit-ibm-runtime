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

"""Unit tests for draw_chunk_timings."""

from datetime import datetime, timedelta

import ddt

from qiskit_ibm_runtime.quantum_program.quantum_program_result import (
    ChunkPart,
    ChunkSpan,
    ChunkTiming,
    Metadata,
    QuantumProgramResult,
)
from qiskit_ibm_runtime.visualization import draw_chunk_timings

from ...ibm_test_case import IBMTestCase


def _make_chunk_timings(n: int = 5) -> ChunkTiming:
    """Create a synthetic ChunkTiming with ``n`` chunks."""
    t = datetime(year=2025, month=1, day=1)
    spans = []
    for i in range(n):
        start = t + timedelta(seconds=i * 10)
        stop = start + timedelta(seconds=5 + i)
        parts = [ChunkPart(idx_item=i % 2, size=10 + i)]
        spans.append(ChunkSpan(start=start, stop=stop, parts=parts))
    return ChunkTiming(spans)


@ddt.ddt
class TestDrawChunkTiming(IBMTestCase):
    """Tests for ``draw_chunk_timings`` and ``ChunkTiming``."""

    def setUp(self):
        """Set up the test class."""
        self.chunk_timings = _make_chunk_timings()

    def test_len(self):
        """Assert ChunkTiming reports the number of spans it contains."""
        self.assertEqual(len(self.chunk_timings), 5)

    def test_getitem_int(self):
        """Assert integer indexing returns a ChunkSpan."""
        item = self.chunk_timings[0]
        self.assertIsInstance(item, ChunkSpan)

    def test_getitem_slice(self):
        """Assert slice indexing returns a new ChunkTiming with the selected spans."""
        sliced = self.chunk_timings[1:3]
        self.assertIsInstance(sliced, ChunkTiming)
        self.assertEqual(len(sliced), 2)

    def test_iter(self):
        """Assert iteration yields all ChunkSpan objects."""
        items = list(self.chunk_timings)
        self.assertEqual(len(items), 5)
        self.assertTrue(all(isinstance(s, ChunkSpan) for s in items))

    def test_eq(self):
        """Assert two ChunkTiming built from the same spans compare equal."""
        other = _make_chunk_timings()
        self.assertEqual(self.chunk_timings, other)

    def test_repr(self):
        """Assert repr includes the class name."""
        self.assertIn("ChunkTiming", repr(self.chunk_timings))

    def test_start_stop_duration(self):
        """Assert start and stop are datetimes and duration is positive."""
        self.assertIsInstance(self.chunk_timings.start, datetime)
        self.assertIsInstance(self.chunk_timings.stop, datetime)
        self.assertGreater(self.chunk_timings.duration, 0)

    @ddt.data(False, True)
    def test_draw_normalize_y(self, normalize_y):
        """Verify draw_chunk_timings renders without error with normalize_y on and off."""
        fig = draw_chunk_timings(self.chunk_timings, normalize_y=normalize_y)
        self.save_plotly_artifact(fig)

    def test_draw_common_start(self):
        """Verify draw_chunk_timings renders without error when common_start=True."""
        fig = draw_chunk_timings(self.chunk_timings, common_start=True)
        self.save_plotly_artifact(fig)

    def test_draw_with_name(self):
        """Verify draw_chunk_timings renders without error when a name is provided."""
        fig = draw_chunk_timings(self.chunk_timings, names="my_job")
        self.save_plotly_artifact(fig)

    def test_draw_empty(self):
        """Verify draw_chunk_timings handles an empty ChunkTiming without error."""
        fig = draw_chunk_timings(ChunkTiming([]))
        self.save_plotly_artifact(fig)

    @ddt.data(
        (False, False, 4, None),
        (True, True, 8, "alpha"),
        (True, False, 4, ["alpha", "beta"]),
    )
    @ddt.unpack
    def test_two_chunk_timings(self, normalize_y, common_start, width, names):
        """Verify draw_chunk_timings renders two ChunkTiming for cross-job comparison."""
        ct2 = _make_chunk_timings(n=3)
        fig = draw_chunk_timings(
            self.chunk_timings,
            ct2,
            normalize_y=normalize_y,
            common_start=common_start,
            line_width=width,
            names=names,
        )
        self.save_plotly_artifact(fig)

    def test_draw_method(self):
        """Verify ChunkTiming.draw() renders without error."""
        fig = self.chunk_timings.draw()
        self.save_plotly_artifact(fig)

    def test_draw_method_normalize_y(self):
        """Verify ChunkTiming.draw() renders without error when normalize_y=True."""
        fig = self.chunk_timings.draw(normalize_y=True)
        self.save_plotly_artifact(fig)

    def test_result_chunk_timings_property(self):
        """Assert QuantumProgramResult.chunk_timings wraps the metadata spans."""
        metadata = Metadata(chunk_timing=list(self.chunk_timings))
        result = QuantumProgramResult(data=[], metadata=metadata)
        self.assertIsInstance(result.timing, ChunkTiming)
        self.assertEqual(len(result.timing), len(self.chunk_timings))

    def test_result_chunk_timings_empty(self):
        """Assert QuantumProgramResult.chunk_timings is empty when no metadata spans are present."""
        result = QuantumProgramResult(data=[])
        self.assertIsInstance(result.timing, ChunkTiming)
        self.assertEqual(len(result.timing), 0)
