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

"""Utility functions for executor-based Estimator post-processors."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from qiskit.quantum_info import Pauli

# Mapping for projecting observable terms to Z computational basis
CHAR_TO_Z_CHARS = (
    dict.fromkeys(["Z", "X", "Y"], "Z")
    | dict.fromkeys(["0", "+", "r"], "0")
    | dict.fromkeys(["1", "-", "l"], "1")
    | {"I": "I"}
)


def identify_measure_basis(pauli: Pauli, measure_bases: list[tuple[Pauli, int]]) -> int:
    """Find which measurement basis can measure the given Pauli.

    A basis is compatible if, on every qubit where ``pauli`` is non-identity,
    the basis measures the exact same Pauli axis. Identity positions in
    ``pauli`` may correspond to any axis in the measurement basis.

    Args:
        pauli: Pauli operator to measure.
        measure_bases: List of (measurement_basis, config_idx) tuples.

    Returns:
        The config_idx of the compatible basis.

    Raises:
        ValueError: If no compatible basis found.
    """
    pauli_support = np.logical_or(pauli.z, pauli.x)

    for basis, config_idx in measure_bases:
        # On all non-identity positions of ``pauli``, the measurement basis
        # must match both the z/x symplectic components exactly.
        if np.array_equal(pauli.z[pauli_support], basis.z[pauli_support]) and np.array_equal(
            pauli.x[pauli_support], basis.x[pauli_support]
        ):
            return config_idx

    raise ValueError(f"Cannot compute eval of {pauli} from the given bases elements.")


def project_to_z(term: str) -> np.ndarray[int]:
    """Project observable term to Z computational basis.

    Maps X,Y,Z → "Z", projectors 0,1,+,-,r,l → "0"/"1", I → "I"

    Args:
        term: Observable term string.

    Returns:
        Array of projected characters.
    """
    return np.array([CHAR_TO_Z_CHARS[ch] for ch in str(term)])


def compute_evals(
    observable_term: str, datum: np.ndarray, signs: np.ndarray | None = None
) -> np.ndarray:
    """Compute the per-shot eigenvalue for a single observable term.

    This is a building block used by :func:`compute_exp_val`. It's kept separate so
    that callers can combine several terms' eigenvalues *before* computing statistics
    on them, which is needed to correctly account for terms that share the same shots.

    Args:
        observable_term: Observable term string (e.g., ``"ZZZ"``, ``"0X1"``, ``"IXI"``).
        datum: Boolean measurement outcomes, shape
            ``(num_randomizations, shots_per_randomization, num_qubits)``.
        signs: Optional PEC sign array, shape
            ``(num_randomizations, error_generators_indicators)``.

    Returns:
        Float array of per-shot eigenvalues, shape
        ``(num_randomizations, shots_per_randomization)``.
        Shots that do not satisfy a projector condition are set to ``0``.
    """
    z_term = project_to_z(observable_term)

    # Reverse to match endian-ness
    is_Z = (z_term == "Z")[::-1]
    is_0 = (z_term == "0")[::-1]
    is_1 = (z_term == "1")[::-1]

    any_0s = np.any(is_0)
    any_1s = np.any(is_1)
    any_Zs = np.any(is_Z)

    if any_Zs:
        evals = np.prod(1 - 2 * datum[..., is_Z], axis=-1).astype(float)
    else:
        evals = np.ones(datum.shape[:-1], dtype=float)

    # In case signs is provided - multiply the evals by -1 if the parity of the signs is odd
    if signs is not None:
        signs_per_rand = np.asarray(np.sum(signs, axis=-1) % 2, dtype=bool)
        signs_per_rand = 1 - 2 * signs_per_rand
        evals *= signs_per_rand[..., np.newaxis]

    # Apply projector filters for "0" and "1"
    if any_0s | any_1s:
        keep = np.ones(datum.shape[:-1], dtype=bool)
        if any_0s:
            keep &= np.all(~datum[..., is_0], axis=-1)
        if any_1s:
            keep &= np.all(datum[..., is_1], axis=-1)
        evals = np.where(keep, evals, 0.0)

    return evals


def variances_from_evals(evals: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Compute ensemble variance and twirl variance from a combined per-shot evals array.

    ``evals`` should already combine all terms that share the same measurement shots
    (i.e. the same ``config_idx``), so that cross-covariances between those terms are
    captured correctly.

    Args:
        evals: Combined per-shot values, shape ``(num_randomizations, shots_per_randomization)``.

    Returns:
        Tuple ``(ensemble_variance, twirl_variance)``:

        - ``ensemble_variance``: variance treating all shots as a single ensemble.
        - ``twirl_variance``: variance of per-randomization means across randomizations.
          Equal to ``ensemble_variance`` when ``num_randomizations == 1``.
    """
    num_randomizations = evals.shape[0]
    shots_per_randomization = evals.shape[1]
    total_shots = num_randomizations * shots_per_randomization

    exp_val = np.sum(evals) / total_shots
    ensemble_variance = np.sum(evals**2) / total_shots - exp_val**2

    if num_randomizations == 1:
        twirl_variance = ensemble_variance
    else:
        twirl_exp_vals = np.sum(evals, axis=-1) / shots_per_randomization
        twirl_variance = np.var(twirl_exp_vals, ddof=0)

    return np.asarray(ensemble_variance), np.asarray(twirl_variance)


def compute_exp_val(
    observable_term: str, datum: np.ndarray, signs: np.ndarray | None = None
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Compute expectation value and variances of an observable term from measurement data.

    Args:
        observable_term: Observable term string (e.g., "ZZZ", "0X1", "IXI")
        datum: Boolean array of measurement outcomes, shape
            (num_randomizations, shots_per_randomization, num_qubits)
        signs: Optional boolean array used with probabilistic error cancellation (PEC). Indicates
            which errors were inserted in each circuit randomization, shape
             (num_randomizations, error_generators_indicators)

    Returns:
        Tuple of (expectation_value, ensemble_variance, twirl_variance):
            - expectation_value: Mean expectation value across all shots
            - ensemble_variance: Variance treating all shots as a single ensemble
            - twirl_variance: Variance of expectation values across twirls
    """
    evals = compute_evals(observable_term, datum, signs)
    num_randomizations = datum.shape[0]
    shots_per_randomization = datum.shape[-2]
    total_shots = num_randomizations * shots_per_randomization
    exp_val = np.sum(evals) / total_shots
    # Reshape to (R, S) so variances_from_evals gets a clean 2D array.
    evals_2d = evals.reshape(num_randomizations, shots_per_randomization)
    ensemble_variance, twirl_variance = variances_from_evals(evals_2d)
    return np.asarray(exp_val), ensemble_variance, twirl_variance
