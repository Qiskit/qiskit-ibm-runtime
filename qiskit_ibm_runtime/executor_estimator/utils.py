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

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from qiskit.primitives.containers.estimator_pub import ObservablesArray

import numpy as np
from qiskit.quantum_info import Pauli, PauliList

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
