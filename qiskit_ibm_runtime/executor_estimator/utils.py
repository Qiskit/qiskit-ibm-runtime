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

"""Helper functions for wrapper EstimatorV2.

NOTE: At least some of these functions are temporary and will be moved to a
permanent location (qiskit-addons or qiskit core) in the future.
"""

from __future__ import annotations

from functools import lru_cache

import numpy as np
from qiskit.quantum_info import Pauli

# Lookup table for converting Pauli characters to samplomatic integers
LOOKUP_TABLE = {"I": 0, "Z": 1, "X": 2, "Y": 3}

# Mapping for projecting observable terms to Z computational basis
CHAR_TO_Z_CHARS = (
    dict.fromkeys(["Z", "X", "Y"], "Z")
    | dict.fromkeys(["0", "+", "r"], "0")
    | dict.fromkeys(["1", "-", "l"], "1")
    | {"I": "I"}
)


def get_pauli_basis(basis: str) -> Pauli:
    """Map computational basis to Pauli measurement basis.

    Converts basis strings like "000", "++0", "rl1" to Pauli operators.
    - 0, 1 → Z
    - +, - → X
    - r, l → Y
    - I → I

    Args:
        basis: Basis string to convert.

    Returns:
        Pauli operator representing the measurement basis.
    """
    basis = (
        basis.replace("0", "Z")
        .replace("1", "Z")
        .replace("+", "X")
        .replace("-", "X")
        .replace("r", "Y")
        .replace("l", "Y")
    )
    return Pauli(basis)


def pauli_to_ints(pauli: Pauli) -> list[int]:
    """Convert Pauli to list of ints following samplomatic convention.

    I→0, Z→1, X→2, Y→3

    Args:
        pauli: Pauli operator to convert.

    Returns:
        List of integers representing the Pauli.

    Note:
        pauli.to_label() returns big-endian (leftmost = highest qubit),
        but samplomatic expects little-endian (leftmost = qubit 0),
        so we reverse the list.
    """
    return [LOOKUP_TABLE[p] for p in pauli.to_label()][::-1]


def unbroadcast_index(
    bc_index: tuple[int | slice, ...], shape: tuple[int, ...]
) -> tuple[int | slice, ...]:
    """Index an array using an index from a compatible broadcasted shape.

    An ND-array ``arr`` is broadcastable to any shape ``bc_shape = (*pad_shape, *arr.shape)``.
    This function allows indexing ``arr`` using an ND-index or slice from ``bc_shape`` and
    will return the index for ``arr`` that accesses the same value.

    Args:
        bc_index: An ND-index from a broadcasted shape.
        shape: The shape of the broadcasting compatible array to index.

    Returns:
        The equivalent un-broadcasted ND-index of the array with specified shape.
    """

    @lru_cache
    def _pad_broadcast_shape(shape: tuple[int, ...], ndims: int) -> tuple[int | slice, ...]:
        # Pad a shape with trivial dimensions.
        shape_ndims = len(shape)
        pad = ndims - shape_ndims
        if pad > 0:
            return pad * (1,) + shape
        return shape

    shape_ndims = len(shape)
    if shape_ndims == 0:
        return ()

    pad_shape = _pad_broadcast_shape(shape, len(bc_index))
    bc_index = tuple(0 if dim == 1 else i for i, dim in zip(bc_index, pad_shape))
    return bc_index[-shape_ndims:]


def project_to_z(term: str) -> np.ndarray[int]:
    """Project observable term to Z computational basis.

    Maps X,Y,Z → "Z", projectors 0,1,+,-,r,l → "0"/"1", I → "I"

    Args:
        term: Observable term string.

    Returns:
        Array of projected characters.
    """
    return np.array([CHAR_TO_Z_CHARS[ch] for ch in str(term)])


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


def compute_exp_val(
    observable_term: str, datum: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Compute expectation value and variances of an observable term from measurement data.

    Args:
        observable_term: Observable term string (e.g., "ZZZ", "0X1", "IXI")
        datum: Boolean array of measurement outcomes, shape
            (num_randomizations, shots_per_randomization, num_qubits)

    Returns:
        Tuple of (expectation_value, ensemble_variance, twirl_variance):
            - expectation_value: Mean expectation value across all shots
            - ensemble_variance: Variance treating all shots as a single ensemble
            - twirl_variance: Variance of expectation values across twirls
    """
    z_term = project_to_z(observable_term)

    # Compute masks
    # Reverse to match endian-ness
    is_Z = (z_term == "Z")[::-1]
    is_0 = (z_term == "0")[::-1]
    is_1 = (z_term == "1")[::-1]

    any_0s = np.any(is_0)
    any_1s = np.any(is_1)
    any_Zs = np.any(is_Z)

    if any_Zs:
        evals = np.prod(1 - 2 * datum[..., is_Z], axis=-1)
    else:
        evals = np.ones(datum.shape[:-1])

    # Apply projector filters for "0" and "1"
    if any_0s | any_1s:
        keep = np.ones(datum.shape[:-1], dtype=bool)
        if any_0s:
            keep &= np.all(~datum[..., is_0], axis=-1)
        if any_1s:
            keep &= np.all(datum[..., is_1], axis=-1)
        evals = np.where(keep, evals, 0)

    # evals shape: (num_randomizations, shots_per_randomization)
    # evals contains expectation values for each shot (may be 0 for filtered shots)
    num_randomizations = datum.shape[0]
    shots_per_randomization = datum.shape[-2]
    total_shots = num_randomizations * shots_per_randomization

    # Compute overall expectation value (mean across all shots)
    exp_val = np.sum(evals) / total_shots

    # Compute ensemble variance: treating all shots as a single ensemble
    # variance = E[X²] - E[X]²
    evals_squared = evals**2
    mean_squared = np.sum(evals_squared) / total_shots
    ensemble_variance = mean_squared - exp_val**2

    # Compute twirl variance: variance of expectation values across twirls
    # When num_randomizations=1 (no twirling), twirl_variance should equal ensemble_variance
    # so that stds and ensemble_standard_error are equal
    if num_randomizations == 1:
        twirl_variance = ensemble_variance
    else:
        # For each twirl (randomization), compute the expectation value
        # Must normalize by shots_per_randomization (not actual count) to handle filtered shots
        # Compute variance of these per-twirl expectation values
        twirl_exp_vals = (
            np.sum(evals, axis=-1) / shots_per_randomization
        )  # Shape: (num_randomizations,)
        twirl_variance = np.var(twirl_exp_vals, ddof=0)

    # Ensure we always return numpy arrays (even for scalar results)
    return np.asarray(exp_val), np.asarray(ensemble_variance), np.asarray(twirl_variance)
