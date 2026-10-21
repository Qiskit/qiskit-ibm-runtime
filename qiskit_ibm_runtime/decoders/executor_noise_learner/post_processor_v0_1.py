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

# def unmasked_shot_percentages(raw_data: RawData) -> tuple[dict[int, float], float]:
#     """Average percentage of unmasked shots per fragment depth.

#     Walks every leaf of the raw data's datatree and splits its randomizations into two groups by
#     whether the unbound instruction sequence has a non-empty repeatable fragment:

#     * non-empty repeatable fragment (the vanilla sequences), bucketed by fragment depth;
#     * empty repeatable fragment (the SPAM sequences), pooled into a single value.

#     For each randomization, the percentage of surviving shots is ``100 * (1 - data_mask.mean())``,
#     since ``data_mask`` is True exactly for the shots to exclude.

#     Args:
#         raw_data: The raw data, after any post-selection stages have been applied.

#     Returns:
#         A tuple ``(vanilla, spam)``, where ``vanilla`` maps fragment depth to the average
#         percentage of unmasked shots, and ``spam`` is the single corresponding average over the
#         sequences with an empty repeatable fragment (NaN if there are none).
#     """
#     vanilla = defaultdict(list)
#     spam = []

#     for _, node in raw_data.datatree.items():
#         dataset = node.dataset
#         if "data_mask" not in dataset:
#             continue

#         percentages = 100.0 * (1.0 - dataset["data_mask"].values.mean(axis=-1))
#         sequences = dataset["unbound_instruction_sequence"].values
#         depths = dataset["fragment_depth"].values

#         for sequence, depth, percentage in zip(sequences, depths, percentages):
#             bucket = vanilla[int(depth)] if sequence.repeatable_fragment else spam
#             bucket.append(float(percentage))

#     return (
#         {depth: float(np.mean(values)) for depth, values in sorted(vanilla.items())},
#         float(np.mean(spam)) if spam else float("nan"),
#     )


@HAS_QNL.require_in_call
def noise_learner_v3_post_processor_v0_1(result: QuantumProgramResult) -> NoiseLearnerV3Results:
    """Convert a quantum program result to noise learner results for NoiseLearnerV3.

    Args:
        result: The raw quantum program result.

    Returns:
        A :class:`~qiskit_ibm_runtime.results.NoiseLearnerV3Results`, with one
        :class:`~qiskit_ibm_runtime.results.NoiseLearnerV3Result` per user-provided layer.
    """
    print(f"{result.passthrough_data.keys()=}")
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

    depths = options["layer_pair_depths"]
    physical_qubits = [0]  # TODO
    fraction_kept = dict.fromkeys(depths, 1.0)
    success_rates = {depth: dict.fromkeys(physical_qubits, 1.0) for depth in depths}
    post_selection_metadata = {
        "fraction_kept": fraction_kept,
        "success_rates": success_rates,
    }

    return NoiseLearnerV3Results(
        [
            NoiseLearnerV3Result.from_generators(
                generators=[
                    QubitSparsePauliList.from_qubit_sparse_paulis([pauli])
                    for pauli in plm.generators()
                ],
                rates=plm.rates,
                metadata=post_selection_metadata,  # type: ignore[arg-type]
            )
            for plm in noise_maps
        ]
    )
