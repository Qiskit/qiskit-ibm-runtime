# This code is part of Qiskit.
#
# (C) Copyright IBM 2025.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Transport conversion functions"""

from __future__ import annotations

from dataclasses import asdict

import numpy as np
from samplomatic.tensor_interface import TensorSpecification, PauliLindbladMapSpecification

from ibm_quantum_schemas.models.executor.version_0_1.models import (
    ParamsModel,
    CircuitItemModel,
    SamplexItemModel,
    QuantumProgramModel,
    QuantumProgramResultModel,
)
from ibm_quantum_schemas.models.pauli_lindblad_map_model import PauliLindbladMapModel
from ibm_quantum_schemas.models.samplex_model import SamplexModelSSV1
from ibm_quantum_schemas.models.tensor_model import F64TensorModel, TensorModel
from ibm_quantum_schemas.models.qpy_model import QpyModelV13ToV16


from .quantum_program import QuantumProgram, CircuitItem, SamplexItem
from .quantum_program_result import QuantumProgramResult, ChunkPart, ChunkSpan, Metadata
from ..options.executor_options import ExecutorOptions


def quantum_program_to_0_1(program: QuantumProgram, options: ExecutorOptions) -> ParamsModel:
    """Convert a :class:`~.QuantumProgram` to a V0.1 model."""
    model_items = []
    for item in program.items:
        chunk_size = "auto" if item.chunk_size is None else item.chunk_size
        if isinstance(item, CircuitItem):
            model_item = CircuitItemModel(
                circuit=QpyModelV13ToV16.from_quantum_circuit(item.circuit, qpy_version=16),
                circuit_arguments=F64TensorModel.from_numpy(item.circuit_arguments),
                chunk_size=chunk_size,
            )
        elif isinstance(item, SamplexItem):
            arguments = {}
            for spec in item.samplex_arguments.specs:
                if spec.name in item.samplex_arguments:
                    name, value = spec.name, item.samplex_arguments[spec.name]
                    if isinstance(spec, TensorSpecification) or isinstance(value, np.ndarray):
                        arguments[name] = TensorModel.from_numpy(value)
                    elif isinstance(spec, PauliLindbladMapSpecification):
                        arguments[name] = PauliLindbladMapModel.from_pauli_lindblad_map(value)
                    else:
                        arguments[name] = value
            model_item = SamplexItemModel(
                circuit=QpyModelV13ToV16.from_quantum_circuit(item.circuit, qpy_version=16),
                samplex=SamplexModelSSV1.from_samplex(item.samplex, ssv=1),
                samplex_arguments=arguments,
                shape=item.shape,
                chunk_size=chunk_size,
            )
        else:
            raise ValueError(f"Item {item} is not valid.")
        model_items.append(model_item)

    return ParamsModel(
        quantum_program=QuantumProgramModel(shots=program.shots, items=model_items),
        options=asdict(options.execution),  # type: ignore[call-overload]
    )


def quantum_program_result_from_0_1(model: QuantumProgramResultModel) -> QuantumProgramResult:
    """Convert a V0.1 model to a :class:`QuantumProgramResult`."""
    metadata = Metadata(
        chunk_timing=[
            ChunkSpan(
                span.start, span.stop, [ChunkPart(part.idx_item, part.size) for part in span.parts]
            )
            for span in model.metadata.chunk_timing
        ]
    )
    return QuantumProgramResult(
        data=[{name: val.to_numpy() for name, val in item.results.items()} for item in model.data],
        metadata=metadata,
    )
