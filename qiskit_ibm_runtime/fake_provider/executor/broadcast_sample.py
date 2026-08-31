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

"""Utilities for sampling from a Samplex over broadcast and randomization axes."""

from __future__ import annotations

from math import prod
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from samplomatic.samplex import Samplex
    from samplomatic.tensor_interface import TensorInterface


def broadcast_sample(
    samplex: Samplex,
    samplex_arguments: TensorInterface,
    shape: tuple[int, ...],
    rng: np.random.Generator,
) -> dict[str, np.ndarray]:
    """Sample from a samplex, iterating over broadcast axes in ``samplex_arguments``.

    Axes where ``samplex_arguments`` has size > 1 (after right-aligning with
    ``shape``) are **broadcast** axes (e.g. a parameter sweep); the remaining
    axes are **randomization** axes.  For each slice along the broadcast axes
    the function calls ``samplex.sample()`` with scalar (non-broadcastable)
    arguments and the appropriate ``num_randomizations``, then assembles the
    results into arrays of shape ``(*shape, *intrinsic)``.


    Args:
        samplex: The samplex to sample from.
        samplex_arguments: The broadcastable array inputs to the samplex.
        shape: The total shape.
        rng: A randomness generator.

    Returns:
        Broadcasted samples from the samplex.
    """
    ndim = len(shape)
    padded_shape = (1,) * (ndim - samplex_arguments.ndim) + samplex_arguments.shape

    broadcast_axes = [idx for idx in range(ndim) if padded_shape[idx] > 1]
    randomization_axes = [idx for idx in range(ndim) if padded_shape[idx] <= 1]

    num_randomizations = prod(shape[i] for i in randomization_axes)
    rand_shape = tuple(shape[i] for i in randomization_axes)
    broadcast_shape = tuple(shape[i] for i in broadcast_axes)

    output: dict[str, np.ndarray] = {}
    for bc_idx in np.ndindex(broadcast_shape):
        bc_iter = iter(bc_idx)
        slice_idxs = tuple(next(bc_iter) if dim > 1 else 0 for dim in samplex_arguments.shape)

        sample_result = samplex.sample(
            samplex_arguments[slice_idxs],
            num_randomizations=num_randomizations,
            rng=rng,
        )

        if not output:
            for key, val in dict(sample_result).items():
                intrinsic_shape = val.shape[1:]
                output[key] = np.empty((*shape, *intrinsic_shape), dtype=val.dtype)

        bc_iter = iter(bc_idx)
        out_idx = tuple(next(bc_iter) if dim > 1 else slice(None) for dim in padded_shape)

        for key, val in dict(sample_result).items():
            output[key][out_idx] = val.reshape(*rand_shape, *val.shape[1:])

    return output
