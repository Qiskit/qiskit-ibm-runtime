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

"""Utility functions for executor-based SamplerV2."""

from __future__ import annotations
from collections import defaultdict
from collections.abc import Sequence
from typing import Any

from qiskit_ibm_runtime.execution_span import DoubleSliceSpan, TwirledSliceSpanV2
from qiskit_ibm_runtime.quantum_program.quantum_program_result import ChunkSpan, Metadata

from qiskit_ibm_runtime.executor.routines.sampler_v2 import SamplerOptions
from qiskit_ibm_runtime.executor.routines.utils import calculate_twirling_shots


def executor_metadata_to_sampler_metadata(
    metadata: Metadata,
    options: SamplerOptions,
    pubs_shapes: list[tuple[int, ...]],
    shots: int,
) -> dict[str, Any]:
    """Helper to map result metadata for executor job to result metadata for sampler jobs.

    This function is meant to be used when post-processing results for an executor job triggered
    by a SamplerV2.

    Args:
        metadata: The executor metadata.
        options: The options of the sampler job.
        pubs_shapes: The shapes of the PUBs in the sampler job.
        shots: The shots per sampler PUB.

    Returns:
        A dictionary of metadata compatible with the format expected for a SamplerV2 job.
    """
    spans: Sequence[TwirledSliceSpanV2 | DoubleSliceSpan] = []
    if options.twirling.enable_gates or options.twirling.enable_measure:
        spans = _spans_for_twirled_execution(metadata, options, pubs_shapes, shots)
    else:
        spans = _spans_for_untwirled_execution(metadata, pubs_shapes, shots)

    return {"execution": {"execution_spans": spans}}


def _spans_for_twirled_execution(
    metadata: Metadata,
    options: SamplerOptions,
    pubs_shapes: list[tuple[int, ...]],
    shots: int,
) -> list[TwirledSliceSpanV2]:
    """Helper to compute spans when twirling is ON."""
    num_randomizations, shots_per_randomization = calculate_twirling_shots(
        shots,
        options.twirling.num_randomizations,
        options.twirling.shots_per_randomization,
    )

    spans = []
    for span in metadata.chunk_timing:
        _validate_chunk_span(span, pubs_shapes)

        # The dictionary of slices required to initialize a ``TwirledSliceSpanV2``
        slices = {}

        # A map from part indices to the latest element included in a slice
        slices_latest_stop: dict[int, int] = defaultdict(int)

        for part in span.parts:
            slice_start = slices_latest_stop[part.idx_item]
            slice_stop = slice_start + part.size
            slices_latest_stop[part.idx_item] = slice_stop

            # a shape tuple including a twirling axis, and where the last axis is shots per randomization
            twirled_shape = (
                (num_randomizations,) + pubs_shapes[part.idx_item] + (shots_per_randomization,)
            )

            # whether ``num_randomizations`` is at the front of the tuple, as opposed to right before the
            # ``shots`` axis at the end
            at_front = True

            # a slice of an array of shape ``twirled_shape[:-1]``, flattened
            shape_slice = slice(slice_start, slice_stop)

            # a slice of ``twirled_shape[-1]``
            shots_slice = slice(0, shots)

            # the number of shots requested for the pub
            pub_shots = shots

            slices[part.idx_item] = (twirled_shape, at_front, shape_slice, shots_slice, pub_shots)

        spans.append(TwirledSliceSpanV2(span.start, span.stop, slices))

    return spans


def _spans_for_untwirled_execution(
    metadata: Metadata,
    pubs_shapes: list[tuple[int, ...]],
    shots: int,
) -> list[DoubleSliceSpan]:
    """Helper to compute spans when twirling is OFF."""
    spans = []
    for span in metadata.chunk_timing:
        _validate_chunk_span(span, pubs_shapes)

        # The dictionary of slices required to initialize a ``DoubleSliceSpan``
        slices = {}

        # A map from part indices to the latest element included in a slice
        slices_latest_stop: dict[int, int] = defaultdict(int)

        for part in span.parts:
            slice_start = slices_latest_stop[part.idx_item]
            slice_stop = slice_start + part.size
            slices_latest_stop[part.idx_item] = slice_stop

            shape_tuple = pubs_shapes[part.idx_item] + (shots,)
            flat_shape_slice = slice(slice_start, slice_stop)
            shots_slice = slice(0, shots)
            slices[part.idx_item] = (shape_tuple, flat_shape_slice, shots_slice)
        spans.append(DoubleSliceSpan(span.start, span.stop, slices))

    return spans


def _validate_chunk_span(span: ChunkSpan, pubs_shapes: list[tuple[int, ...]]) -> None:
    if max({part.idx_item for part in span.parts}) >= len(pubs_shapes):
        raise ValueError("Not enough pub shapes.")
