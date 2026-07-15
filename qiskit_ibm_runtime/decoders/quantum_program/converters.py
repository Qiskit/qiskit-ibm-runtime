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

from ...results.quantum_program import (
    ChunkPart,
    ChunkSpan,
    ItemMetadata,
    Metadata,
    QuantumProgramItemResult,
    QuantumProgramResult,
    SchedulerTiming,
    StretchValues,
)

if TYPE_CHECKING:
    from ibm_quantum_schemas.executor.version_0_1 import QuantumProgramResultModel

from ...quantum_program.converters.converters_0_2 import passthrough_data_from_0_2
from ...quantum_program.converters.converters_1_0 import passthrough_data_from_1_0
from ...quantum_program.converters.converters_1_1 import passthrough_data_from_1_1
from ...quantum_program.converters.converters_2_0 import passthrough_data_from_2_0


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
        data=[
            QuantumProgramItemResult({name: val.to_numpy() for name, val in item.results.items()})
            for item in model.data
        ],
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

    data = []
    for item in model.data:
        timings = item.metadata.scheduler_timing
        scheduler_timing = SchedulerTiming(**dict(timings)) if timings else None

        stretches = item.metadata.stretch_values
        stretch_values = [StretchValues(**dict(s)) for s in stretches] if stretches else None

        data.append(
            QuantumProgramItemResult(
                result={name: val.to_numpy() for name, val in item.results.items()},
                metadata=ItemMetadata(
                    scheduler_timing=scheduler_timing, stretch_values=stretch_values
                ),
            )
        )

    return QuantumProgramResult(
        data=data,
        metadata=metadata,
        passthrough_data=passthrough_data_from_0_2(model.passthrough_data),
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

    data = []
    for item in model.data:
        timings = item.metadata.scheduler_timing
        scheduler_timing = SchedulerTiming(**dict(timings)) if timings else None

        stretches = item.metadata.stretch_values
        stretch_values = [StretchValues(**dict(s)) for s in stretches] if stretches else None

        data.append(
            QuantumProgramItemResult(
                result={name: val.to_numpy() for name, val in item.results.items()},
                metadata=ItemMetadata(
                    scheduler_timing=scheduler_timing, stretch_values=stretch_values
                ),
            )
        )

    result = QuantumProgramResult(
        data=data,
        metadata=metadata,
        passthrough_data=passthrough_data_from_1_0(model.passthrough_data),
    )
    result._semantic_role = model.semantic_role
    return result


def quantum_program_result_from_1_1(model: QuantumProgramResultModel) -> QuantumProgramResult:
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

    data = []
    for item in model.data:
        timings = item.metadata.scheduler_timing
        scheduler_timing = SchedulerTiming(**dict(timings)) if timings else None

        stretches = item.metadata.stretch_values
        stretch_values = [StretchValues(**dict(s)) for s in stretches] if stretches else None

        data.append(
            QuantumProgramItemResult(
                result={name: val.to_numpy() for name, val in item.results.items()},
                metadata=ItemMetadata(
                    scheduler_timing=scheduler_timing, stretch_values=stretch_values
                ),
            )
        )

    result = QuantumProgramResult(
        data=data,
        metadata=metadata,
        passthrough_data=passthrough_data_from_1_1(model.passthrough_data),
    )
    result._semantic_role = model.semantic_role
    return result


def quantum_program_result_from_2_0(model: QuantumProgramResultModel) -> QuantumProgramResult:
    """Convert a V2.0 model to a :class:`QuantumProgramResult`."""
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

    data = []
    for item in model.data:
        timings = item.metadata.scheduler_timing
        scheduler_timing = SchedulerTiming(**dict(timings)) if timings else None

        stretches = item.metadata.stretch_values
        stretch_values = [StretchValues(**dict(s)) for s in stretches] if stretches else None

        data.append(
            QuantumProgramItemResult(
                result={name: val.to_numpy() for name, val in item.results.items()},
                metadata=ItemMetadata(
                    scheduler_timing=scheduler_timing, stretch_values=stretch_values
                ),
            )
        )

    result = QuantumProgramResult(
        data=data,
        metadata=metadata,
        passthrough_data=passthrough_data_from_2_0(model.passthrough_data),
    )
    result._semantic_role = model.semantic_role
    return result
