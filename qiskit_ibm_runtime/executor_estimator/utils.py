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
    from qiskit.primitives import EstimatorPub

from qiskit_ibm_runtime.exceptions import IBMInputValueError
from qiskit.quantum_info import Pauli
from functools import lru_cache


# Lookup table for converting Pauli characters to samplomatic integers
LOOKUP_TABLE = {"I": 0, "Z": 1, "X": 2, "Y": 3}


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
    # Extract precision from pubs
    pub_precisions = {pub.precision or run_precision for pub in pubs}

    if len(pub_precisions) != 1:
        raise IBMInputValueError(
            f"All pubs must have the same precision. Found: {pub_precisions}"
            "(possibly via the run provided precision parameter)"
        )

    return next(iter(pub_precisions))
