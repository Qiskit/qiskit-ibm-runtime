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

"""Tests the class ``QuantumProgramResult``."""

from datetime import datetime, timedelta, timezone

import numpy as np
from ddt import ddt
from samplomatic.quantum_program import ChunkPart, ChunkSpan, ChunkTiming

from qiskit_ibm_runtime.results.quantum_program import (
    ItemMetadata,
    Metadata,
    QuantumProgramItemResult,
    QuantumProgramResult,
    SchedulerTiming,
    StretchValues,
)

from ...ibm_test_case import IBMTestCase
from ...utils import combine


def _make_span(start_s: float, stop_s: float, size: int = 1) -> ChunkSpan:
    """Helper to build a ``ChunkSpan`` with a single ``ChunkPart``."""
    epoch = datetime(2025, 1, 1, tzinfo=timezone.utc)
    return ChunkSpan(
        start=epoch + timedelta(seconds=start_s),
        stop=epoch + timedelta(seconds=stop_s),
        parts=[ChunkPart(idx_item=0, size=size)],
    )


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


class TestQuantumProgramResult(IBMTestCase):
    """Tests the ``QuantumProgramResult`` class."""

    def test_quantum_program_result(self):
        """Tests the ``QuantumProgramResult`` class."""
        meas1 = np.array([[False], [True], [True]])
        meas2 = np.array([[True, True], [True, False], [False, False]])
        meas_flips = np.array([[False, False]])

        result1 = QuantumProgramItemResult({"meas": meas1})
        result2 = QuantumProgramItemResult({"meas": meas2, "measurement_flips.meas": meas_flips})
        result = QuantumProgramResult([result1, result2])

        # test __len__
        self.assertEqual(len(result), 2)

        # test __iter__
        for res, expected_res in zip(result, [result1, result2]):
            self.assertEqual(res, expected_res)

        # test __getitem__
        self.assertEqual([result[0], result[1]], [result1, result2])

    def test_wraps_metadata_spans(self):
        """Test `timing` returns a ChunkTiming backed by the metadata's spans."""
        spans = [_make_span(0, 1, size=10), _make_span(2, 3, size=5)]
        result = QuantumProgramResult([], metadata=Metadata(chunk_timing=spans))
        self.assertIsInstance(result.timing, ChunkTiming)
        self.assertEqual(list(result.timing), spans)

    def test_empty_metadata(self):
        """Test `timing` is empty when no spans are present in metadata."""
        result = QuantumProgramResult([])
        self.assertEqual(len(result.timing), 0)


@ddt
class TestQuantumProgramItemResult(IBMTestCase):
    """Tests the ``QuantumProgramItemResult`` class."""

    @combine(
        stretch_values=[None, [StretchValues("name", 2, 3, [(0, 1)])]],
        scheduler_timing=[None, SchedulerTiming("dt", 10)],
    )
    def test_quantum_program_item_result(self, stretch_values, scheduler_timing):
        """Tests the ``QuantumProgramItemResult`` class."""
        meas = np.array([[False], [True], [True]])
        meas_flips = np.array([[False, False]])

        metadata = ItemMetadata(stretch_values=stretch_values, scheduler_timing=scheduler_timing)

        item_result = QuantumProgramItemResult(
            {"meas": meas, "measurement_flips.meas": meas_flips}, metadata
        )
        self.assertTrue((item_result["meas"] == meas).all())
        self.assertTrue((item_result["measurement_flips.meas"] == meas_flips).all())
        self.assertEqual(item_result.metadata, metadata)


@ddt
class TestChunkTiming(IBMTestCase):
    """Tests for ``ChunkTiming``."""

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
