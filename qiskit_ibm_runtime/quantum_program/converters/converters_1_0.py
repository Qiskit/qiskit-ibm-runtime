# This code is part of Qiskit.
#
# (C) Copyright IBM 2025-2026.
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

from dataclasses import asdict
from datetime import timezone

import numpy as np
from samplomatic.tensor_interface import TensorSpecification, PauliLindbladMapSpecification

from qiskit.circuit import QuantumCircuit
from ibm_quantum_schemas.executor.version_1_0 import (
    ParamsModel,
    CircuitItemModel,
    SamplexItemModel,
    QuantumProgramModel,
    QuantumProgramResultModel,
)
from ibm_quantum_schemas.common import (
    PauliLindbladMapModel,
    SamplexModelSSV1ToSSV3,
    F64TensorModel,
    TensorModel,
    QpyDataV13ToV17Model,
)
from ...utils.utils import get_qpy_version, get_ssv_version


from ..quantum_program import QuantumProgram, CircuitItem, SamplexItem
from ..quantum_program_result import QuantumProgramResult, ChunkPart, ChunkSpan, Metadata
from ...options.executor_options import ExecutorOptions


def quantum_program_from_1_0(model: ParamsModel) -> tuple[QuantumProgram, ExecutorOptions]:
    """Convert a V1.0 model to a pair of program and options."""
    program_model = model.quantum_program
    circuits: list[QuantumCircuit] = program_model.circuits.to_python(use_cached=True)
    items: list[CircuitItem | SamplexItem] = []
    for circuit, model_item in zip(circuits, program_model.items):
        chunk_size = None if model_item.chunk_size == "auto" else model_item.chunk_size

        if model_item.item_type == "circuit":
            items.append(
                CircuitItem(
                    circuit=circuit,
                    circuit_arguments=model_item.circuit_arguments.to_numpy(),
                    chunk_size=chunk_size,
                )
            )
        elif model_item.item_type == "samplex":
            samplex = model_item.samplex.to_samplex(use_cached=True)
            samplex_arguments = samplex.inputs().make_broadcastable()
            for name, value in model_item.samplex_arguments.items():
                if isinstance(value, TensorModel):
                    samplex_arguments[name] = value.to_numpy()
                elif isinstance(value, PauliLindbladMapModel):
                    samplex_arguments[name] = value.to_pauli_lindblad_map()
                else:
                    samplex_arguments[name] = value

            items.append(
                SamplexItem(
                    circuit=circuit,
                    samplex=samplex,
                    samplex_arguments=samplex_arguments,
                    chunk_size=chunk_size,
                    shape=tuple(model_item.shape),
                )
            )
        else:
            raise ValueError("Unexpected model item type.")

    quantum_program = QuantumProgram(
        shots=program_model.shots,
        items=items,
        meas_level=program_model.meas_level,
        passthrough_data=program_model.passthrough_data,
    )
    quantum_program._semantic_role = program_model.semantic_role

    options = ExecutorOptions()
    model_options = model.options.model_copy(deep=True)
    options.execution.init_qubits = model_options.init_qubits
    options.execution.rep_delay = model_options.rep_delay
    options.experimental = model_options.experimental

    return quantum_program, options


def quantum_program_to_1_0(program: QuantumProgram, options: ExecutorOptions) -> ParamsModel:
    """Convert a :class:`~.QuantumProgram` to a V1.0 model."""
    model_items = []
    circuits = []
    for item in program.items:
        circuits.append(item.circuit)
        chunk_size = "auto" if item.chunk_size is None else item.chunk_size
        if isinstance(item, CircuitItem):
            model_item = CircuitItemModel(
                circuit_arguments=F64TensorModel.from_numpy(item.circuit_arguments),
                chunk_size=chunk_size,
                shape=[],  # Not yet supported
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
                samplex=SamplexModelSSV1ToSSV3.from_samplex(item.samplex, ssv=get_ssv_version(3)),
                samplex_arguments=arguments,
                shape=item.shape,
                chunk_size=chunk_size,
            )
        else:
            raise ValueError(f"Item {item} is not valid.")
        model_items.append(model_item)

    # Build options dict starting with execution options
    options_dict = asdict(options.execution)  # type: ignore[call-overload]

    # Add experimental options if provided
    if options.experimental:
        options_dict["experimental"] = options.experimental

    return ParamsModel(
        quantum_program=QuantumProgramModel(
            shots=program.shots,
            circuits=QpyDataV13ToV17Model.from_python(circuits, qpy_version=get_qpy_version(17)),
            items=model_items,
            meas_level=program.meas_level,
            passthrough_data=program.passthrough_data,
        ),
        options=options_dict,
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
