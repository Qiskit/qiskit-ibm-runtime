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

"""Post-processing for the client-side noise learner: delegates to qiskit-noise-learning."""

from __future__ import annotations

from typing import TYPE_CHECKING

from qiskit.quantum_info import QubitSparsePauliList
from qiskit_noise_learning.protocols import process_learning_results

from ...results.noise_learner_v3 import NoiseLearnerV3Result, NoiseLearnerV3Results

if TYPE_CHECKING:
    from ...results.quantum_program import QuantumProgramResult


def noise_learner_v3_post_processor_v0_1(result: QuantumProgramResult) -> NoiseLearnerV3Results:
    """Convert a quantum program result to a noise learner result for NoiseLearnerV3.

    Args:
        result: The raw quantum program result.

    Returns:
        A :class:`~qiskit_ibm_runtime.results.NoiseLearnerV3Results`, with one
        :class:`~qiskit_ibm_runtime.results.NoiseLearnerV3Result` per gate in the model.
    """
    result_fit = process_learning_results(result)
    maps = result_fit.model.to_pauli_lindblad_maps(
        result_fit.model_data, restrict_to_qubit_idxs=True
    )  # type: ignore
    return NoiseLearnerV3Results(
        [
            NoiseLearnerV3Result.from_generators(
                generators=[
                    QubitSparsePauliList.from_qubit_sparse_paulis([pauli])
                    for pauli in plm.generators()
                ],
                rates=plm.rates,
                metadata={"gate_name": gate_name},
            )
            for gate_name, plm in maps.items()
        ]
    )
