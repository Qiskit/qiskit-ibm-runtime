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

"""Helper functions for the Twirled Readout Error eXtinction (TREX) post-processing."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from qiskit.quantum_info import Pauli

    from ...results.quantum_program import QuantumProgramItemResult

import numpy as np
from qiskit.quantum_info import PauliLindbladMap, QubitSparsePauli

from .utils import project_to_z


def get_processed_calibration_data(calibration_result: QuantumProgramItemResult) -> np.ndarray:
    """Process data from TREX calibration circuit results.

    Args:
        calibration_result: QuantumProgramItemResult of the TREX calibration circuit.

    Returns:
        TREX flipped calibration data.
    """
    if "_trex_cal" not in calibration_result:
        raise ValueError("Dedicated TREX calibration circuit is missing from the results.")

    trex_noise_calibration_data = calibration_result["_trex_cal"]
    trex_calibration_measurement_flips = calibration_result["measurement_flips._trex_cal"]
    return np.logical_xor(trex_noise_calibration_data, trex_calibration_measurement_flips)


def calculate_trex_factor(
    noise_data: PauliLindbladMap | np.ndarray, observable_term: Pauli | str
) -> float:
    """Calculate TREX factor relevant for a given observable term based on noise model.

    Args:
        noise_data: PauliLindbladMap containing measurement noise model or a result of TREX
            calibration execution.
        observable_term: observable term to calculate TREX factor for.

    Returns:
        TREX factor for the observable term.
    """
    # Reverse to match the qubit ordering: the rightmost character is qubit 0.
    z_term = project_to_z(observable_term)[::-1]

    # Every non-identity operator--meaning both Pauli Zs and projectors in `z_term`--
    # is treated as a Pauli Z, regardless of whether the term is a Pauli
    # or a projector, since the TREX factor only depends on the readout-error support.
    indices = np.where(z_term != "I")[0]

    if isinstance(noise_data, PauliLindbladMap):
        z_sparse_pauli = QubitSparsePauli(("Z" * len(indices), indices), num_qubits=len(z_term))
        return 1 / noise_data.pauli_fidelity(z_sparse_pauli)

    evals = np.prod(1 - 2 * noise_data[..., indices], axis=-1)
    shots = noise_data.shape[0] * noise_data.shape[-2]  # randomizations * shots_per_randomizations

    # Compute trex factor
    return 1 / (np.sum(evals) / shots)
