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

"""Tests for ``executor_metadata_to_sampler_metadata``."""

from __future__ import annotations

import unittest
from datetime import datetime

from qiskit_ibm_runtime.execution_span import DoubleSliceSpan, TwirledSliceSpanV2
from qiskit_ibm_runtime.results.quantum_program import ChunkSpan, Metadata, ChunkPart

from qiskit_ibm_runtime.decoders.executor_sampler.utils import (
    executor_metadata_to_sampler_metadata,
)


class TestExecutorMetadataToSamplerMetadata(unittest.TestCase):
    """Tests for ``executor_metadata_to_sampler_metadata``."""

    def test_without_twirling(self):
        """Test mapping metadata when twirling is OFF."""
        chunk_timing = [
            ChunkSpan(
                start=datetime(2025, 12, 30, 14, 10),
                stop=datetime(2025, 12, 30, 14, 15),
                parts=[ChunkPart(idx_item=0, size=10), ChunkPart(idx_item=1, size=20)],
            ),
            ChunkSpan(
                start=datetime(2025, 12, 30, 14, 10),
                stop=datetime(2025, 12, 30, 14, 15),
                parts=[ChunkPart(idx_item=0, size=5)],
            ),
        ]
        metadata = Metadata(chunk_timing=chunk_timing)

        sampler_metadata = executor_metadata_to_sampler_metadata(
            metadata, 0, shots := 1000, pubs_shapes := [(3, 5), (20,)]
        )

        spans = sampler_metadata["execution"]["execution_spans"]

        expected_spans = [
            DoubleSliceSpan(
                chunk_timing[0].start,
                chunk_timing[0].stop,
                data_slices={
                    0: (pubs_shapes[0] + (shots,), slice(0, 10), slice(0, shots)),
                    1: (pubs_shapes[1] + (shots,), slice(0, 20), slice(0, shots)),
                },
            ),
            DoubleSliceSpan(
                chunk_timing[1].start,
                chunk_timing[1].stop,
                data_slices={
                    0: (pubs_shapes[0] + (shots,), slice(10, 15), slice(0, shots)),
                },
            ),
        ]

        self.assertEqual(spans, expected_spans)

    def test_with_twirling(self):
        """Test mapping metadata when twirling is ON."""
        chunk_timing = [
            ChunkSpan(
                start=datetime(2025, 12, 30, 14, 10),
                stop=datetime(2025, 12, 30, 14, 15),
                parts=[ChunkPart(idx_item=0, size=10), ChunkPart(idx_item=1, size=20)],
            ),
            ChunkSpan(
                start=datetime(2025, 12, 30, 14, 10),
                stop=datetime(2025, 12, 30, 14, 15),
                parts=[ChunkPart(idx_item=0, size=5)],
            ),
        ]
        metadata = Metadata(chunk_timing=chunk_timing)
        sampler_metadata = executor_metadata_to_sampler_metadata(
            metadata, num_randomizations := 5, shots_per_randomization := 7, [(3, 5), (20,)]
        )

        spans = sampler_metadata["execution"]["execution_spans"]

        expected_spans = [
            TwirledSliceSpanV2(
                chunk_timing[0].start,
                chunk_timing[0].stop,
                {
                    0: (
                        (num_randomizations, 3, 5, shots_per_randomization),
                        True,
                        slice(0, 10),
                        slice(0, 7),
                        35,
                    ),
                    1: (
                        (num_randomizations, 20, shots_per_randomization),
                        True,
                        slice(0, 20),
                        slice(0, 7),
                        35,
                    ),
                },
            ),
            TwirledSliceSpanV2(
                chunk_timing[1].start,
                chunk_timing[1].stop,
                {
                    0: (
                        (num_randomizations, 3, 5, shots_per_randomization),
                        True,
                        slice(10, 15),
                        slice(0, 7),
                        35,
                    )
                },
            ),
        ]

        self.assertEqual(spans, expected_spans)

    def test_incorrect_pub_shapes_raises(self):
        """Test that an error is raised when pub shapes is of incorrect lenght."""
        chunk_timing = [
            ChunkSpan(
                start=datetime(2025, 12, 30, 14, 10),
                stop=datetime(2025, 12, 30, 14, 15),
                parts=[ChunkPart(idx_item=0, size=10), ChunkPart(idx_item=1, size=20)],
            ),
            ChunkSpan(
                start=datetime(2025, 12, 30, 14, 10),
                stop=datetime(2025, 12, 30, 14, 15),
                parts=[ChunkPart(idx_item=0, size=5)],
            ),
        ]
        metadata = Metadata(chunk_timing=chunk_timing)

        pub_shapes = [(3, 5)]

        with self.assertRaisesRegex(ValueError, expected_regex="Not enough pub shapes."):
            executor_metadata_to_sampler_metadata(metadata, 0, 1000, pub_shapes)

        with self.assertRaisesRegex(ValueError, expected_regex="Not enough pub shapes."):
            executor_metadata_to_sampler_metadata(metadata, 2, 1000, pub_shapes)
