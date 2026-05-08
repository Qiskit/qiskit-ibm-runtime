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
from typing import TYPE_CHECKING

from ibm_quantum_schemas.common import F64TensorModel, QpyModelV13ToV17
from ibm_quantum_schemas.noise_learner_v3.version_0_2 import (
    NoiseLearnerV3ResultModel,
    NoiseLearnerV3ResultsModel,
    ParamsModel,
)
from qiskit.circuit import QuantumCircuit

from ...options_models import NoiseLearnerV3Options
from ...utils.utils import get_qpy_version
from ...results.noise_learner_v3 import (
    NoiseLearnerV3Results,
)

if TYPE_CHECKING:
    from collections.abc import Iterable

    from qiskit.circuit import CircuitInstruction

EXECUTION_FIELDS = {"init_qubits", "rep_delay"}
"""Fields that belong to ``options.execution`` in user-land, but in ``options`` in schemas."""


def noise_learner_v3_inputs_to_0_2(
    instructions: Iterable[CircuitInstruction],
    options: NoiseLearnerV3Options,
) -> ParamsModel:
    """Convert noise learner V3 inputs a V0.2 model."""
    qubits = list({qubit for instr in instructions for qubit in instr.qubits})
    clbits = list({clbit for instr in instructions for clbit in instr.clbits})

    circuit = QuantumCircuit(list(qubits), list(clbits))
    for instr in instructions:
        circuit.append(instr, instr.qubits, instr.clbits)

    # Convert `options` to dict, moving the fields in `options.execution` to top-level.
    schema_options = asdict(options)  # type: ignore[call-overload]
    for field in EXECUTION_FIELDS:
        schema_options[field] = schema_options["execution"][field]
    schema_options.pop("execution")

    return ParamsModel(
        instructions=QpyModelV13ToV17.from_quantum_circuit(
            circuit, qpy_version=get_qpy_version(17)
        ),
        options=schema_options,  # type: ignore[call-overload]
    )


def noise_learner_v3_inputs_from_0_2(
    model: ParamsModel,
) -> tuple[list[CircuitInstruction], NoiseLearnerV3Options]:
    """Convert a V0.2 model to noise learner V3 inputs."""
    instructions = list(model.instructions.to_quantum_circuit())

    # Convert `model.options` to dict, moving the fields that are part of `options.execution` from
    # top-level.
    top_level_dump = model.options.model_dump(exclude_none=True, exclude=EXECUTION_FIELDS)
    top_level_dump["execution"] = model.options.model_dump(
        exclude_none=True, include=EXECUTION_FIELDS
    )

    options = NoiseLearnerV3Options(**top_level_dump)
    return instructions, options


def noise_learner_v3_result_to_0_2(
    result: NoiseLearnerV3Results,
) -> NoiseLearnerV3ResultsModel:
    """Convert noise learner v3 results to a V0.2 model."""
    return NoiseLearnerV3ResultsModel(
        data=[
            NoiseLearnerV3ResultModel(
                generators_sparse=[gen.to_sparse_list() for gen in datum._generators],
                num_qubits=datum._generators[0].num_qubits,
                rates=F64TensorModel.from_numpy(datum._rates),
                rates_std=F64TensorModel.from_numpy(datum._rates_std),
                metadata=datum.metadata,
            )
            for datum in result.data
        ],
    )
