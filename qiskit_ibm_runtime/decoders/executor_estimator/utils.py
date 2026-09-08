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

from functools import lru_cache

import numpy as np
from qiskit.quantum_info import Pauli

# Mapping for projecting observable terms to Z computational basis
CHAR_TO_Z_CHARS = (
    dict.fromkeys(["Z", "X", "Y"], "Z")
    | dict.fromkeys(["0", "+", "r"], "0")
    | dict.fromkeys(["1", "-", "l"], "1")
    | {"I": "I"}
)


def project_to_z(term: str) -> np.ndarray[int]:
    """Project observable term to Z computational basis.

    Maps X,Y,Z → "Z", projectors 0,1,+,-,r,l → "0"/"1", I → "I"

    Args:
        term: Observable term string.

    Returns:
        Array of projected characters.
    """
    return np.array([CHAR_TO_Z_CHARS[ch] for ch in str(term)])


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
