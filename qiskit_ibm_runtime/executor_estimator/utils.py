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

"""Helper functions for observable processing in EstimatorV2.

NOTE: These functions are temporary and will be moved to a permanent location
(qiskit-addons or qiskit core) in the future.
"""

from __future__ import annotations

import numpy as np
from qiskit.quantum_info import Pauli, PauliList
from qiskit.primitives.containers.estimator_pub import ObservablesArray
from ..exceptions import IBMInputValueError
from qiskit.primitives.containers.estimator_pub import EstimatorPub

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


def get_bases(observables: ObservablesArray) -> PauliList:
    """Find minimal set of measurement bases for all observable terms.

    Groups commuting Pauli terms and returns one basis per group.
    Uses qubit-wise commutation checking.

    Args:
        observables: Array of observables to measure.

    Returns:
        PauliList of measurement bases.
    """
    all_bases = []

    # Convert to numpy array of dicts using __array__() method
    # This works for both scalar (shape=()) and array cases
    obs_array = np.asarray(observables)

    # Use np.ndenumerate to iterate over all elements
    for _, obs_dict in np.ndenumerate(obs_array):
        for term, coeff in obs_dict.items():
            basis = get_pauli_basis(term)
            all_bases.append(basis)

    # Handle empty case
    if not all_bases:
        raise ValueError(
            "No measurement bases found. Observables array is empty or contains no terms."
        )

    groups = PauliList(all_bases).group_commuting(qubit_wise=True)
    bases = PauliList(
        [((np.logical_or.reduce(group.z), np.logical_or.reduce(group.x))) for group in groups]
    )

    # Filter out all-identity bases (where both z and x are all False)
    non_identity_bases = []
    for basis in bases:
        if np.any(basis.z) or np.any(basis.x):
            non_identity_bases.append(basis)

    # Handle identity case
    if not non_identity_bases:
        raise ValueError("No measurement bases found. Only identity in the observables.")

    return PauliList(non_identity_bases)


def project_to_z(term: str) -> np.ndarray:
    """Project observable term to Z computational basis.

    Maps X,Y,Z → "Z", projectors 0,1,+,-,r,l → "0"/"1", I → "I"

    Args:
        term: Observable term string.

    Returns:
        Array of projected characters.
    """
    return np.array([CHAR_TO_Z_CHARS[ch] for ch in str(term)])


def identify_measure_basis(pauli: Pauli, measure_bases: list[Pauli]) -> int:
    """Find which measurement basis can measure the given Pauli.

    A basis is compatible if, on every qubit where ``pauli`` is non-identity,
    the basis measures the exact same Pauli axis. Identity positions in
    ``pauli`` may correspond to any axis in the measurement basis.

    Args:
        pauli: Pauli operator to measure.
        measure_bases: List of available measurement bases.

    Returns:
        Index of the first compatible basis.

    Raises:
        ValueError: If no compatible basis found.
    """
    pauli_support = np.logical_or(pauli.z, pauli.x)

    for basis_idx, basis in enumerate(measure_bases):
        # On all non-identity positions of ``pauli``, the measurement basis
        # must match both the z/x symplectic components exactly.
        if np.array_equal(pauli.z[pauli_support], basis.z[pauli_support]) and np.array_equal(
            pauli.x[pauli_support], basis.x[pauli_support]
        ):
            return basis_idx

    raise ValueError(f"Cannot compute eval of {pauli} from the given bases elements.")


def compute_exp_val(observable_term: str, datum: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Compute expectation value and variance of an observable term from measurement data.

    Args:
        observable_term: Observable term string (e.g., "ZZZ", "0X1", "IXI")
        datum: Boolean array of measurement outcomes, shape
            (num_randomizations, ..., shots_per_randomization, num_qubits)

    Returns:
        Tuple of (expectation_values, variance), each with shape (...,)

    Algorithm:
    1. Project term to Z basis
    2. Compute eigenvalues: prod(1 - 2*bit) for Z positions
    3. Apply projector filters for 0/1 positions
    4. Average over shots and randomizations for expectation value
    5. Compute variance: E[X²] - E[X]²
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

    shots = datum.shape[0] * datum.shape[-2]  # randomizations * shots_per_randomizations

    # Compute expectation value
    exp_val = np.sum(evals, axis=(0, -1)) / shots

    # Compute standard deviation (standard error of the mean)
    # variance = E[X²] - E[X]²
    evals_squared = evals**2
    mean_squared = np.sum(evals_squared, axis=(0, -1)) / shots
    variance = mean_squared - exp_val**2

    # Ensure we always return numpy arrays (even for scalar results)
    return np.asarray(exp_val), np.asarray(variance)


def resolve_precision(
    pubs: list[EstimatorPub],
    run_precision: float | None = None,
) -> float | None:
    """Resolve precision from multiple sources with clear precedence.

    Precedence order (highest to lowest):
    1. Individual pub precision (must be consistent across all pubs)
    2. run() method precision parameter (run_precision)

    Args:
        pubs: List of estimator pubs (may contain precision values).
        run_precision: Precision specified in run() method.

    Returns:
        The resolved precision value, or None if no precision is specified anywhere.

    Raises:
        IBMInputValueError: If pubs have different precision values.
    """
    # Extract precision from pubs, using fallback for pubs without explicit precision
    pub_precisions = {pub.precision if pub.precision is not None else run_precision for pub in pubs}

    # Remove None if it's still there (no precision specified anywhere)
    pub_precisions = {p for p in pub_precisions if p is not None}

    if not pub_precisions:
        return None

    if len(pub_precisions) != 1:
        raise IBMInputValueError(f"All pubs must have the same precision. Found: {pub_precisions}")

    return next(iter(pub_precisions))
