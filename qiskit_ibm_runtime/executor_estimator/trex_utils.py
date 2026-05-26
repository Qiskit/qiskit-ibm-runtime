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

"""Helper functions for the Twirled Readout Error eXtinction (TREX) error mitigation method."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence
    from qiskit.primitives.containers.estimator_pub import EstimatorPub
    from ..options_models.measure_noise_learning_options import MeasureNoiseLearningOptions
    from ..results.quantum_program import QuantumProgramItemResult

import numpy as np
from qiskit.circuit import ClassicalRegister, QuantumCircuit
from qiskit.quantum_info import Pauli, PauliLindbladMap, QubitSparsePauli
from samplomatic import build
from samplomatic.transpiler import generate_boxing_pass_manager

from ..quantum_program.quantum_program import SamplexItem


def create_trex_calibration_circuit(
    pubs: Sequence[EstimatorPub], measure_noise_learning: MeasureNoiseLearningOptions
) -> SamplexItem:
    """Creates a TREX calibration circuit.

    The calibration circuit is based on all circuit terminal measurement layers in all pubs.

    Args:
        pubs: List of estimator pubs to extract relevant qubits from.
        measure_noise_learning: Measure noise learning options.

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
    )
    annotated_trex_circuit = boxing_pm.run(trex_circuit)
    template_trex_circuit, trex_samplex = build(annotated_trex_circuit)
    trex_calibration_item = SamplexItem(
        circuit=template_trex_circuit,
        samplex=trex_samplex,
        shape=(measure_noise_learning.num_randomizations,),
    )

    return trex_calibration_item


def calculate_trex_noise_model(calibration_result: QuantumProgramItemResult) -> PauliLindbladMap:
    """Calculate measurement noise model from TREX calibration circuit results.

    Args:
        calibration_result: QuantumProgramItemResult of the TREX calibration circuit.

    Returns:
        PauliLindbladMap containing measurement noise model.
    """
    if "_trex_cal" not in calibration_result:
        raise ValueError("Dedicated TREX calibration circuit is missing from the results.")

    trex_noise_calibration_data = calibration_result["_trex_cal"]
    trex_calibration_measurement_flips = calibration_result["measurement_flips._trex_cal"]
    trex_noise_calibration_data_flipped = np.logical_xor(
        trex_noise_calibration_data, trex_calibration_measurement_flips
    )
    noise_list = []
    num_qubits = trex_noise_calibration_data.shape[-1]
    for qubit_index in range(num_qubits):
        # the shape of the calibration data is (randomizations, shots, measured_qubit)
        qubit_data = trex_noise_calibration_data_flipped[:, :, qubit_index]
        excited_state_count = np.sum(qubit_data)
        total_shots = len(qubit_data.flatten())
        flip_rate = excited_state_count / total_shots
        noise_list.append(("X", [qubit_index], flip_rate))
    readout_noise = PauliLindbladMap.from_sparse_list(noise_list, num_qubits=num_qubits)
    return readout_noise


def calculate_trex_factor(noise_model: PauliLindbladMap, observable_term: Pauli | str) -> float:
    """Calculate TREX factor relevant for a given observable term based on noise model.

    Args:
        noise_model: PauliLindbladMap containing measurement noise model.
        observable_term: observable term to calculate TREX factor for.

    Returns:
        TREX factor for the observable term.
    """
    sparse_pauli = QubitSparsePauli(observable_term)
    z_sparse_pauli = QubitSparsePauli(
        ("Z" * len(sparse_pauli.indices), sparse_pauli.indices), num_qubits=sparse_pauli.num_qubits
    )
    return 1 / noise_model.pauli_fidelity(z_sparse_pauli)
