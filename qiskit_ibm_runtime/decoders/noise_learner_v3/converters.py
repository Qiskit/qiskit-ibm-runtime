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

from typing import TYPE_CHECKING

from qiskit.quantum_info import QubitSparsePauliList

from ...noise_learner_v3.noise_learner_v3_result import (
    NoiseLearnerV3Result,
    NoiseLearnerV3Results,
)

if TYPE_CHECKING:
    from ibm_quantum_schemas.noise_learner_v3.version_0_2 import (
        NoiseLearnerV3ResultsModel,
    )


def noise_learner_v3_result_from_0_1(
    model: NoiseLearnerV3ResultsModel,
) -> NoiseLearnerV3Results:
    """Convert a V0.1 model to noise learner v3 results."""
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


def noise_learner_v3_result_from_0_2(
    model: NoiseLearnerV3ResultsModel,
) -> NoiseLearnerV3Results:
    """Convert a V0.2 model to noise learner v3 results."""
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
