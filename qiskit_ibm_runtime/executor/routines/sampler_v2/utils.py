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
from typing import Any

from qiskit_ibm_runtime.execution_span import DoubleSliceSpan, TwirledSliceSpanV2
from qiskit_ibm_runtime.quantum_program.quantum_program_result import ChunkSpan, Metadata

def executor_metadata_to_sampler_metadata_v1(
    metadata: Metadata,
    twirling: bool,
    pubs_shapes: list[tuple[int, ...]],
    shots: int,
) -> dict[str, Any]:
    """"""
    spans = []
    for span in metadata.chunk_timing:
        validate_chunk_span(span, pubs_shapes)

        slices = {}
        slices_latest_stop: dict[int, int]  = defaultdict(int)
        for part in span.parts:
            slice_start = slices_latest_stop[part.idx_item]
            slice_stop = slice_start + part.size
            slices_latest_stop[part.idx_item] = slice_stop

            if twirling:
                slices[part.idx_item] = (
                    pubs_shapes[part.idx_item] + (part.size,),
                    True,
                    slice(slice_start, slice_stop),
                    slice(0, shots),
                    shots,
                )
                spans.append(TwirledSliceSpanV2(span.start, span.stop, slices))
            else:
                slices[part.idx_item] = (
                    pubs_shapes[part.idx_item] + (shots,),
                    slice(slice_start, slice_stop),
                    slice(0, shots),
                )
                spans.append(DoubleSliceSpan(span.start, span.stop, slices))

    return {"execution": {"execution_spans": spans}}

def validate_chunk_span(span: ChunkSpan, pubs_shapes: tuple[int, ...]) -> None:
    """"""
    if max({part.idx_item for part in span.parts}) >= len(pubs_shapes):
        raise ValueError("Not enough pub shapes.")

