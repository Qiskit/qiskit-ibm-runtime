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

"""Transport conversion functions."""

from __future__ import annotations

from datetime import timezone
from typing import TYPE_CHECKING

from ...quantum_program.quantum_program_result import (
    ChunkPart,
    ChunkSpan,
    Metadata,
    QuantumProgramResult,
)

if TYPE_CHECKING:
    from ibm_quantum_schemas.executor.version_0_1 import QuantumProgramResultModel


def quantum_program_result_from_0_1(model: QuantumProgramResultModel) -> QuantumProgramResult:
    """Convert a V0.1 model to a :class:`QuantumProgramResult`."""
    metadata = Metadata(
        chunk_timing=[
            ChunkSpan(
                span.start.replace(tzinfo=timezone.utc),
                span.stop.replace(tzinfo=timezone.utc),
                [ChunkPart(part.idx_item, part.size) for part in span.parts],
            )
            for span in model.metadata.chunk_timing
        ]
    )
    return QuantumProgramResult(
        data=[{name: val.to_numpy() for name, val in item.results.items()} for item in model.data],
        metadata=metadata,
    )


def quantum_program_result_from_0_2(model: QuantumProgramResultModel) -> QuantumProgramResult:
    """Convert a V0.2 model to a :class:`QuantumProgramResult`."""
    metadata = Metadata(
        chunk_timing=[
            ChunkSpan(
                span.start.replace(tzinfo=timezone.utc),
                span.stop.replace(tzinfo=timezone.utc),
                [ChunkPart(part.idx_item, part.size) for part in span.parts],
            )
            for span in model.metadata.chunk_timing
        ]
    )

    return QuantumProgramResult(
        data=[{name: val.to_numpy() for name, val in item.results.items()} for item in model.data],
        metadata=metadata,
        passthrough_data=model.passthrough_data,
    )


def quantum_program_result_from_1_0(model: QuantumProgramResultModel) -> QuantumProgramResult:
    """Convert a V1.0 model to a :class:`QuantumProgramResult`."""
    metadata = Metadata(
        chunk_timing=[
            ChunkSpan(
                span.start.replace(tzinfo=timezone.utc),
                span.stop.replace(tzinfo=timezone.utc),
                [ChunkPart(part.idx_item, part.size) for part in span.parts],
            )
            for span in model.metadata.chunk_timing
        ]
    )

    result = QuantumProgramResult(
        data=[{name: val.to_numpy() for name, val in item.results.items()} for item in model.data],
        metadata=metadata,
        passthrough_data=model.passthrough_data,
    )
    result._semantic_role = model.semantic_role
    return result
