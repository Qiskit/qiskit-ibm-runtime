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

import datetime

import numpy as np

from qiskit_ibm_runtime.quantum_program.quantum_program_result import (
    ChunkPart,
    ChunkSpan,
    ChunkTiming,
    Metadata,
    QuantumProgramResult,
    QuantumProgramItemResult,
)

from ...ibm_test_case import IBMTestCase


def _make_span(start_s: float, stop_s: float, size: int = 1) -> ChunkSpan:
    """Helper to build a ``ChunkSpan`` with a single ``ChunkPart``."""
    epoch = datetime.datetime(2025, 1, 1, tzinfo=datetime.timezone.utc)
    return ChunkSpan(
        start=epoch + datetime.timedelta(seconds=start_s),
        stop=epoch + datetime.timedelta(seconds=stop_s),
        parts=[ChunkPart(idx_item=0, size=size)],
    )


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


class TestChunkTiming(IBMTestCase):
    """Tests the ``ChunkTiming`` class."""

    def test_len_and_iter(self):
        """Supports len() and iteration over the wrapped spans."""
        spans = [_make_span(0, 1), _make_span(1, 2), _make_span(2, 3)]
        timing = ChunkTiming(spans)
        self.assertEqual(len(timing), 3)
        self.assertEqual(list(timing), spans)

    def test_getitem_int(self):
        """Integer indexing returns the corresponding ChunkSpan."""
        spans = [_make_span(0, 1), _make_span(1, 2)]
        timing = ChunkTiming(spans)
        self.assertEqual(timing[0], spans[0])
        self.assertEqual(timing[1], spans[1])

    def test_getitem_slice(self):
        """Slice indexing returns a new ChunkTiming."""
        spans = [_make_span(i, i + 1) for i in range(4)]
        sliced = ChunkTiming(spans)[1:3]
        self.assertIsInstance(sliced, ChunkTiming)
        self.assertEqual(list(sliced), spans[1:3])

    def test_start_stop_duration(self):
        """start, stop, and duration are derived from the spans."""
        spans = [_make_span(10, 20, size=3), _make_span(25, 40, size=7)]
        timing = ChunkTiming(spans)
        epoch = datetime.datetime(2025, 1, 1, tzinfo=datetime.timezone.utc)
        self.assertEqual(timing.start, epoch + datetime.timedelta(seconds=10))
        self.assertEqual(timing.stop, epoch + datetime.timedelta(seconds=40))
        self.assertAlmostEqual(timing.duration, 30.0)
