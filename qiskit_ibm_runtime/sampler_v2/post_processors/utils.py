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

"""Utility functions for executor-based SamplerV2 post-processors."""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING, Any

import numpy as np

from qiskit_ibm_runtime.execution_span import DoubleSliceSpan, TwirledSliceSpanV2
from qiskit_ibm_runtime.quantum_program.quantum_program_result import QuantumProgramItemResult

if TYPE_CHECKING:
    from collections.abc import Sequence

    from qiskit_ibm_runtime.quantum_program.quantum_program_result import ChunkSpan, Metadata


def executor_metadata_to_sampler_metadata(
    metadata: Metadata,
    num_randomizations: int,
    shots: int,
    pubs_shapes: list[tuple[int, ...]],
) -> dict[str, Any]:
    """Helper to map result metadata for executor job to result metadata for sampler jobs.

    This function is meant to be used when post-processing results for an executor job triggered
    by a SamplerV2.

    Args:
        metadata: The executor metadata.
        num_randomizations: The number of randomizations per PUB, where ``0`` means that twirling
            was not enabled.
        shots: The shots per PUB. This corresponds to ``pub.shots`` if twirling was not enabled,
            and to ``shots_per_randomization`` if twirling was enabled.
        pubs_shapes: The shapes of the PUBs in the sampler job.

    Returns:
        A dictionary of metadata compatible with the format expected for a SamplerV2 job.
    """
    spans: Sequence[TwirledSliceSpanV2 | DoubleSliceSpan] = []
    if num_randomizations != 0:
        spans = _spans_for_twirled_execution(metadata, num_randomizations, shots, pubs_shapes)
    else:
        spans = _spans_for_untwirled_execution(metadata, shots, pubs_shapes)

    return {"execution": {"execution_spans": spans}}


def _spans_for_twirled_execution(
    metadata: Metadata,
    num_randomizations: int,
    shots_per_randomization: int,
    pubs_shapes: list[tuple[int, ...]],
) -> list[TwirledSliceSpanV2]:
    """Helper to compute spans when twirling is ON."""
    # A map from part indices to the latest element included in a slice
    slices_latest_stop: dict[int, int] = defaultdict(int)

    spans = []
    for span in metadata.chunk_timing:
        _validate_chunk_span(span, pubs_shapes)

        # The dictionary of slices required to initialize a ``TwirledSliceSpanV2``
        slices = {}

        for part in span.parts:
            slice_start = slices_latest_stop[part.idx_item]
            slice_stop = slice_start + part.size
            slices_latest_stop[part.idx_item] = slice_stop

            # A shape tuple including a twirling axis, and where the last axis is shots per
            # randomization.
            twirled_shape = (
                (num_randomizations,) + pubs_shapes[part.idx_item] + (shots_per_randomization,)
            )

            # Whether ``num_randomizations`` is at the front of the tuple, as opposed to right
            # before the ``shots`` axis at the end.
            at_front = True

            # a slice of an array of shape ``twirled_shape[:-1]``, flattened
            shape_slice = slice(slice_start, slice_stop)

            # a slice of ``twirled_shape[-1]``
            shots_slice = slice(0, shots_per_randomization)

            # the number of shots requested for the pub
            pub_shots = num_randomizations * shots_per_randomization

            slices[part.idx_item] = (twirled_shape, at_front, shape_slice, shots_slice, pub_shots)

        spans.append(TwirledSliceSpanV2(span.start, span.stop, slices))

    return spans


def _spans_for_untwirled_execution(
    metadata: Metadata,
    shots: int,
    pubs_shapes: list[tuple[int, ...]],
) -> list[DoubleSliceSpan]:
    """Helper to compute spans when twirling is OFF."""
    # A map from part indices to the latest element included in a slice
    slices_latest_stop: dict[int, int] = defaultdict(int)

    spans = []
    for span in metadata.chunk_timing:
        _validate_chunk_span(span, pubs_shapes)

        # The dictionary of slices required to initialize a ``DoubleSliceSpan``
        slices = {}
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


def flatten_twirling_axes(item: QuantumProgramItemResult, pub_shape: tuple[int, ...]) -> None:
    """Flatten the leading ``num_randomizations`` axis into the shots axis in-place.

    When twirling is enabled, the executor returns measurement data with shape
    ``(num_rand, *pub_shape, shots_per_rand, num_bits)``. This function reshapes
    each array to ``(*pub_shape, total_shots, num_bits)`` where
    ``total_shots = num_rand * shots_per_rand``.

    The function should only be called when twirling was on.

    Args:
        item: Dictionary mapping classical register names to measurement arrays.
            Modified in-place.
        pub_shape: The parameter-sweep shape of the pub (without the leading
            ``num_rand`` axis), e.g. ``()`` for a non-parametric pub or
            ``(3,)`` for a 1-D parameter sweep.
    """
    for creg_name, data in list(item.items()):
        num_rand = data.shape[0]
        shots_per_rand = data.shape[len(pub_shape) + 1]
        total_shots = num_rand * shots_per_rand
        num_bits = data.shape[-1]
        # Move num_rand axis to be adjacent to shots_per_rand before reshaping
        # to avoid mixing randomization indices with parameter sweep indices
        data_reordered = np.moveaxis(data, 0, len(pub_shape))
        # Now shape is (*pub_shape, num_rand, shots_per_rand, num_bits) and is safe for reshaping
        item[creg_name] = data_reordered.reshape(*pub_shape, total_shots, num_bits)
