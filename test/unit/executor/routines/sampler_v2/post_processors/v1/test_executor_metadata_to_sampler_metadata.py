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
from collections import defaultdict
from typing import Any
from datetime import datetime

from qiskit_ibm_runtime.execution_span import DoubleSliceSpan, TwirledSliceSpanV2
from qiskit_ibm_runtime.quantum_program.quantum_program_result import ChunkSpan, Metadata, ChunkPart

from qiskit_ibm_runtime.executor.routines.sampler_v2 import SamplerOptions
from qiskit_ibm_runtime.executor.routines.utils import calculate_twirling_shots

from qiskit_ibm_runtime.executor.routines.sampler_v2.post_processors.v1.executor_metadata_to_sampler_metadata import (
    executor_metadata_to_sampler_metadata,
)


def test_without_twirling():
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

    pub_shapes = [(3, 5), (20,)]

    options = SamplerOptions()
    options.twirling.enable_gates = False
    options.twirling.enable_measure = False

    shots = 1000

    sampler_metadata = executor_metadata_to_sampler_metadata(metadata, options, pub_shapes, shots)

    spans = sampler_metadata["execution"]["execution_spans"]
    assert all(isinstance(span, DoubleSliceSpan) for span in spans)
    assert len(spans) == 2

    assert spans[0].start == chunk_timing[0].start
    assert spans[0].stop == chunk_timing[0].stop
    assert spans[0].pub_idxs == [0, 1]
    assert spans[0].size == sum(part.size for part in chunk_timing[0].parts) * shots

    assert spans[1].start == chunk_timing[1].start
    assert spans[1].stop == chunk_timing[1].stop
    assert spans[1].pub_idxs == [0]
    assert spans[1].size == sum(part.size for part in chunk_timing[1].parts) * shots


def test_with_twirling():
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

    pub_shapes = [(3, 5), (20,)]

    options = SamplerOptions()
    options.twirling.enable_gates = True
    options.twirling.enable_measure = False
    options.twirling.num_randomizations = 5
    options.twirling.shots_per_randomization = 7

    shots = options.twirling.num_randomizations * options.twirling.shots_per_randomization

    sampler_metadata = executor_metadata_to_sampler_metadata(metadata, options, pub_shapes, shots)

    spans = sampler_metadata["execution"]["execution_spans"]
    assert all(isinstance(span, TwirledSliceSpanV2) for span in spans)

    assert len(spans) == 2

    assert spans[0].start == chunk_timing[0].start
    assert spans[0].stop == chunk_timing[0].stop
    assert spans[0].pub_idxs == [0, 1]
    assert (
        spans[0].size
        == sum(part.size for part in chunk_timing[0].parts)
        * options.twirling.shots_per_randomization
    )

    assert spans[1].start == chunk_timing[1].start
    assert spans[1].stop == chunk_timing[1].stop
    assert spans[1].pub_idxs == [0]
    assert (
        spans[1].size
        == sum(part.size for part in chunk_timing[1].parts)
        * options.twirling.shots_per_randomization
    )
