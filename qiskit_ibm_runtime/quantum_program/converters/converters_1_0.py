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

from typing import TYPE_CHECKING

import numpy as np
from ibm_quantum_schemas.common import (
    F64TensorModel,
    PauliLindbladMapModel,
    QpyDataV13ToV17Model,
    SamplexModelSSV1ToSSV3,
    TensorModel,
)
from ibm_quantum_schemas.executor.version_1_0 import (
    CircuitItemModel,
    ParamsModel,
    QuantumProgramModel,
    SamplexItemModel,
)
from samplomatic.tensor_interface import PauliLindbladMapSpecification, TensorSpecification

from ...options_models.executor import ExecutorOptions
from ...utils.utils import get_qpy_version, get_ssv_version
from ..quantum_program import CircuitItem, QuantumProgram, SamplexItem

if TYPE_CHECKING:
    from ibm_quantum_schemas.executor.version_1_0.models import DataTree as DataTreeModel
    from qiskit.circuit import QuantumCircuit

    from ..datatree import DataTree


def passthrough_data_to_1_0(passthrough_data: DataTree) -> DataTreeModel:
    """Convert passthrough data to schema model."""
    if isinstance(passthrough_data, dict):
        return {k: passthrough_data_to_1_0(v) for k, v in passthrough_data.items()}
    if isinstance(passthrough_data, (list, tuple)):
        return [passthrough_data_to_1_0(v) for v in passthrough_data]
    if isinstance(passthrough_data, np.ndarray):
        return TensorModel.from_numpy(passthrough_data)
    return passthrough_data


def passthrough_data_from_1_0(passthrough_data: DataTree) -> DataTreeModel:
    """Convert passthrough data to schema model."""
    if isinstance(passthrough_data, TensorModel):
        return passthrough_data.to_numpy()
    if isinstance(passthrough_data, dict):
        return {k: passthrough_data_from_1_0(v) for k, v in passthrough_data.items()}
    if isinstance(passthrough_data, list):
        return [passthrough_data_from_1_0(el) for el in passthrough_data]
    return passthrough_data


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
        passthrough_data=passthrough_data_from_1_0(program_model.passthrough_data),
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
    options_dict = options.execution.model_dump()

    # Add experimental options if provided
    if options.experimental:
        options_dict["experimental"] = options.experimental

    return ParamsModel(
        quantum_program=QuantumProgramModel(
            shots=program.shots,
            circuits=QpyDataV13ToV17Model.from_python(circuits, qpy_version=get_qpy_version(17)),
            items=model_items,
            meas_level=program.meas_level,
            passthrough_data=passthrough_data_to_1_0(program.passthrough_data),
            semantic_role=program._semantic_role,
        ),
        options=options_dict,
    )
