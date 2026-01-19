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

from collections.abc import Iterable

from ibm_quantum_schemas.models.noise_learner_v3.version_0_1.models import (
    NoiseLearnerV3ResultModel,
    NoiseLearnerV3ResultsModel,
    ParamsModel,
)
from ibm_quantum_schemas.models.qpy_model import QpyModelV13ToV16
from ibm_quantum_schemas.models.tensor_model import F64TensorModel
from qiskit.circuit import CircuitInstruction, QuantumCircuit
from qiskit.quantum_info import QubitSparsePauliList

from ...options import NoiseLearnerV3Options
from ..noise_learner_v3_result import (  # type: ignore[attr-defined]
    NoiseLearnerV3Result,
    NoiseLearnerV3Results,
)


def noise_learner_v3_inputs_to_0_1(
    instructions: Iterable[CircuitInstruction],
    options: NoiseLearnerV3Options,
) -> ParamsModel:
    """Convert noise learner V3 inputs a V0.1 model."""
    qubits = list({qubit for instr in instructions for qubit in instr.qubits})
    clbits = list({clbit for instr in instructions for clbit in instr.clbits})

    circuit = QuantumCircuit(list(qubits), list(clbits))
    for instr in instructions:
        circuit.append(instr, instr.qubits, instr.clbits)

    return ParamsModel(
        instructions=QpyModelV13ToV16.from_quantum_circuit(circuit, qpy_version=16),
        options=options.to_options_model("v0.1"),
    )


def noise_learner_v3_inputs_from_0_1(
    model: ParamsModel,
) -> tuple[list[CircuitInstruction], NoiseLearnerV3Options]:
    """Convert a V0.1 model to noise learner V3 inputs."""
    instructions = list(model.instructions.to_quantum_circuit())
    options = NoiseLearnerV3Options(
        **{key: val for key, val in model.options.model_dump().items() if val}
    )
    return instructions, options


def noise_learner_v3_result_to_0_1(
    result: NoiseLearnerV3Results,
) -> NoiseLearnerV3ResultsModel:
    """Convert noise learner v3 results to a V0.1 model."""
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


def noise_learner_v3_result_from_0_1(
    model: NoiseLearnerV3ResultsModel,
) -> NoiseLearnerV3Results:
    """Convert a V0.1 model to noise learner v3 results"""
    return NoiseLearnerV3Results(
        data=[
            NoiseLearnerV3Result.from_generators(
                generators=[
                    QubitSparsePauliList.from_sparse_list(
                        [tuple(term) for term in sparse_list], datum.num_qubits
                    )
                    for sparse_list in datum.generators_sparse
                ],
                rates=datum.rates.to_numpy(),
                rates_std=datum.rates_std.to_numpy(),
                metadata=datum.metadata.model_dump(),
            )
            for datum in model.data
        ]
    )
