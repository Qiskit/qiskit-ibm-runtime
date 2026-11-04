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
from qiskit_mitigation.postselection.constants import DEFAULT_POST_CHECK_SUFFIX
from qiskit_noise_learning.models import split_pauli_lindblad_model

from ...results.noise_learner_v3 import NoiseLearnerV3Result, NoiseLearnerV3Results
from ...utils.utils import HAS_QNL

if TYPE_CHECKING:
    from ...results.quantum_program import QuantumProgramResult

if HAS_QNL:
    from qiskit_noise_learning.analysis.flip_post_select import (
        FlipPostSelect,
        suffix_creg_identifier,
    )
    from qiskit_noise_learning.protocols.vanilla import (
        _fraction_kept,
        _success_rates,
        process_vanilla_result,
    )


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
        # for pre circuit bit flip checks we specify the registers explicitly to avoid including the
        # "meas0" register
        raw_data_stage = FlipPostSelect(
            creg_identifier=suffix_creg_identifier(["meas0_pre", "spec_pre"]), mode=pre["strategy"]
        )
    if post["enable"]:
        post_stage = FlipPostSelect(
            creg_identifier=suffix_creg_identifier(DEFAULT_POST_CHECK_SUFFIX), mode=post["strategy"]
        )
        raw_data_stage = post_stage if raw_data_stage is None else raw_data_stage + post_stage
    noise_maps, gate_names, fit = process_vanilla_result(result, raw_data_stage=raw_data_stage)

    creg_suffix = None
    if pre["enable"]:
        creg_suffix = ["meas0_pre", "spec_pre"]
    if post["enable"]:
        creg_suffix = (
            DEFAULT_POST_CHECK_SUFFIX
            if creg_suffix is None
            else creg_suffix + [DEFAULT_POST_CHECK_SUFFIX]
        )

    fraction_kept = _fraction_kept(fit.raw_data, gate_names)
    success_rates = _success_rates(
        fit.raw_data, gate_names, suffix_creg_identifier(creg_suffix) if creg_suffix else None
    )

    model_gate_set = split_pauli_lindblad_model(fit.model).model.gate_set
    learning_protocols = [
        "trex" if model_gate_set[name].meas_idxs else "lindblad" for name in gate_names
    ]
    fraction_kept = [
        fk if lp == "lindblad" else fk[0] for fk, lp in zip(fraction_kept, learning_protocols)
    ]
    success_rates = [
        sr if lp == "lindblad" else sr[0] for sr, lp in zip(success_rates, learning_protocols)
    ]
    return NoiseLearnerV3Results(
        [
            NoiseLearnerV3Result.from_generators(
                generators=[
                    QubitSparsePauliList.from_qubit_sparse_paulis([pauli])
                    for pauli in plm.generators()
                ],
                rates=plm.rates,
                metadata={
                    "learning_protocol": lp,
                    "post_selection": {"fraction_kept": fk, "success_rates": sr},
                },
            )
            for plm, lp, fk, sr in zip(noise_maps, learning_protocols, fraction_kept, success_rates)
        ]
    )
