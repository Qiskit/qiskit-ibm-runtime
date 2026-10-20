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

from typing import TYPE_CHECKING, Any

from qiskit.quantum_info import QubitSparsePauliList
from qiskit_mitigation.postselection.constants import (
    DEFAULT_POST_CHECK_SUFFIX,
    DEFAULT_PRE_CHECK_SUFFIX,
)

from ...results.noise_learner_v3 import NoiseLearnerV3Result, NoiseLearnerV3Results
from ...utils.utils import HAS_QNL

if TYPE_CHECKING:
    from ...results.quantum_program import QuantumProgramResult

if HAS_QNL:
    from qiskit_noise_learning.analysis.flip_post_select import (
        FlipPostSelect,
        suffix_creg_identifier,
    )
    from qiskit_noise_learning.protocols import process_vanilla_result


@HAS_QNL.require_in_call
def noise_learner_v3_post_processor_v0_1(result: QuantumProgramResult) -> NoiseLearnerV3Results:
    """Convert a quantum program result to noise learner results for NoiseLearnerV3.

    Args:
        result: The raw quantum program result.

    Returns:
        A :class:`~qiskit_ibm_runtime.results.NoiseLearnerV3Results`, with one
        :class:`~qiskit_ibm_runtime.results.NoiseLearnerV3Result` per user-provided layer.
    """
    if not isinstance(result.passthrough_data, dict):
        raise ValueError(
            "Wrong type for passthrough data: Expected a 'dict', found "
            f"'{type(result.passthrough_data)}'."
        )
    passthrough: dict[str, Any] = result.passthrough_data
    if (post_processor_data := passthrough.get("post_processor")) is None:
        raise ValueError("Missing 'post_processor' in passthrough data.")
    if (options := post_processor_data.get("options", None)) is None:
        raise ValueError("Missing 'options' in passthrough data.")

    pre = options["bit_flip_checks"]["pre_circuit"]
    post = options["bit_flip_checks"]["post_circuit"]

    raw_data_stage = None
    if pre["enable"]:
        raw_data_stage = FlipPostSelect(
            creg_identifier=suffix_creg_identifier(DEFAULT_PRE_CHECK_SUFFIX), mode=pre["strategy"]
        )
    if post["enable"]:
        post_stage = FlipPostSelect(
            creg_identifier=suffix_creg_identifier(DEFAULT_POST_CHECK_SUFFIX), mode=post["strategy"]
        )
        raw_data_stage = raw_data_stage if raw_data_stage is None else raw_data_stage + post_stage
    noise_maps, _, _ = process_vanilla_result(result, raw_data_stage=raw_data_stage)
    return NoiseLearnerV3Results(
        [
            NoiseLearnerV3Result.from_generators(
                generators=[
                    QubitSparsePauliList.from_qubit_sparse_paulis([pauli])
                    for pauli in plm.generators()
                ],
                rates=plm.rates,
            )
            for plm in noise_maps
        ]
    )
