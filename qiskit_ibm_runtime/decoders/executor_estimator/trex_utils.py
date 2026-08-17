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

# Maps each projector character to (pauli_axis, sign_of_pauli_component).
# A projector |v><v| = (I + sign * P) / 2.
_PROJECTOR_TO_PAULI: dict[str, tuple[str, float]] = {
    "0": ("Z", +1.0),  # |0><0| = (I + Z) / 2
    "1": ("Z", -1.0),  # |1><1| = (I - Z) / 2
    "+": ("X", +1.0),  # |+><+| = (I + X) / 2
    "-": ("X", -1.0),  # |-><-| = (I - X) / 2
    "r": ("Y", +1.0),  # |r><r| = (I + Y) / 2
    "l": ("Y", -1.0),  # |l><l| = (I - Y) / 2
}


def expand_obs_dict(obs_dict: dict[str, float]) -> dict[str, float]:
    """Expand an observable dict by decomposing projector terms into pure-Pauli components.

    Every projector character in each term key is expanded using |v><v| = (I ± P) / 2:
      - ``'0'`` → ``(I + Z) / 2``
      - ``'1'`` → ``(I - Z) / 2``
      - ``'+'`` → ``(I + X) / 2``
      - ``'-'`` → ``(I - X) / 2``
      - ``'r'`` → ``(I + Y) / 2``
      - ``'l'`` → ``(I - Y) / 2``

    Pauli characters ``I``, ``X``, ``Y``, ``Z`` pass through unchanged. Coefficients of
    identical pure-Pauli terms that arise from different input entries are summed together.

    If no term contains projector characters the dict is returned unchanged.

    Args:
        obs_dict: Observable dict mapping term strings to real coefficients,
            e.g. ``{"0Z": 0.5, "IZ": 1.0}``.

    Returns:
        A new dict with only pure-Pauli keys (``I/X/Y/Z`` characters) and merged coefficients.

    Examples:
        >>> expand_obs_dict({"0Z": 0.5, "IZ": 1.0})
        {"IZ": 1.25, "ZZ": 0.25}
        >>> expand_obs_dict({"ZZZ": 2.0})
        {"ZZZ": 2.0}
    """
    expanded: dict[str, float] = {}
    for term, coeff in obs_dict.items():
        for sub_term, sub_coeff in _decompose_term(term):
            expanded[sub_term] = expanded.get(sub_term, 0.0) + coeff * sub_coeff
    return expanded


def _decompose_term(term: str) -> list[tuple[str, float]]:
    """Decompose a single observable term string into pure-Pauli (string, coefficient) pairs.

    Each projector character forks the current set of partial terms into two branches
    (identity branch and Pauli branch). Pauli characters pass through unchanged.
    """
    components: list[tuple[str, float]] = [("", 1.0)]
    for ch in term:
        if ch in _PROJECTOR_TO_PAULI:
            pauli_axis, sign = _PROJECTOR_TO_PAULI[ch]
            new_components: list[tuple[str, float]] = []
            for partial_term, partial_coeff in components:
                new_components.append((partial_term + "I", partial_coeff * 0.5))
                new_components.append((partial_term + pauli_axis, partial_coeff * sign * 0.5))
            components = new_components
        else:
            components = [
                (partial_term + ch, partial_coeff) for partial_term, partial_coeff in components
            ]
    return components


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
    sparse_pauli = QubitSparsePauli(observable_term)
    if isinstance(noise_data, PauliLindbladMap):
        z_sparse_pauli = QubitSparsePauli(
            ("Z" * len(sparse_pauli.indices), sparse_pauli.indices),
            num_qubits=sparse_pauli.num_qubits,
        )
        return 1 / noise_data.pauli_fidelity(z_sparse_pauli)
    # The input is a result of TREX calibration execution
    # treat every non identity Pauli as Z
    evals = np.prod(1 - 2 * noise_data[..., sparse_pauli.indices], axis=-1)
    shots = noise_data.shape[0] * noise_data.shape[-2]  # randomizations * shots_per_randomizations

    # Compute trex factor
    return 1 / (np.sum(evals) / shots)
