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

"""Helper functions for the Twirled Readout Error eXtinction (TREX) preparation."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

    from qiskit.primitives.containers.estimator_pub import EstimatorPub

    from ..options_models.measure_noise_learning_options import MeasureNoiseLearningOptions

from qiskit.circuit import ClassicalRegister, QuantumCircuit
from samplomatic import build
from samplomatic.transpiler import generate_boxing_pass_manager

from ..quantum_program.quantum_program import SamplexItem


def resolve_trex_num_randomizations(
    measure_noise_learning: MeasureNoiseLearningOptions,
    twirling_num_randomizations: int,
) -> int:
    """Resolve the number of TREX calibration randomizations.

    ``measure_noise_learning.num_randomizations`` may be an explicit ``int`` or
    ``"auto"``. When ``"auto"``, the TREX calibration uses the same
    number of randomizations as the estimation twirling
    (``twirling_num_randomizations``); an explicit ``int`` is used as-is.

    Args:
        measure_noise_learning: Measure noise learning options.
        twirling_num_randomizations: The number of randomizations used by the
            estimation twirling.

    Returns:
        The number of TREX calibration randomizations to use.
    """
    num_randomizations = measure_noise_learning.num_randomizations
    if num_randomizations == "auto":
        return twirling_num_randomizations
    return num_randomizations


def create_trex_calibration_circuit(
    pubs: Sequence[EstimatorPub],
    num_randomizations: int,
) -> SamplexItem:
    """Creates a TREX calibration circuit.

    The calibration circuit is based on all circuit terminal measurement layers in all pubs.

    Args:
        pubs: List of estimator pubs to extract relevant qubits from.
        num_randomizations: The number of TREX calibration randomizations (already
            resolved, see :func:`~.resolve_trex_num_randomizations`).

    Returns:
        Samplex item containing calibration circuit for TREX factors calculation.
    """
    # create the combined noise learning layer of all given inputs
    max_num_qubits = max(pub.circuit.num_qubits for pub in pubs)

    classical_cal_reg = ClassicalRegister(max_num_qubits, name="_trex_cal")
    trex_circuit = QuantumCircuit(max_num_qubits)
    trex_circuit.add_register(classical_cal_reg)
    trex_circuit.measure_all(add_bits=False)
    boxing_pm = generate_boxing_pass_manager(
        enable_gates=False,
        enable_measures=True,
        measure_annotations="twirl",
        inject_noise_site="after",
    )
    annotated_trex_circuit = boxing_pm.run(trex_circuit)
    template_trex_circuit, trex_samplex = build(annotated_trex_circuit)
    trex_calibration_item = SamplexItem(
        circuit=template_trex_circuit,
        samplex=trex_samplex,
        shape=(num_randomizations,),
    )

    return trex_calibration_item
