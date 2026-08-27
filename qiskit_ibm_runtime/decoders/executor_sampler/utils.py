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

"""Utility functions for executor-based SamplerV2 post-processors."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from ...results.quantum_program import QuantumProgramItemResult

TWIRLING_PREFIX = "measurement_flips."
"""The prefix used to store the twirling bitflips."""


def undo_twirling(item: QuantumProgramItemResult) -> None:
    """Undo twirling bit flips.

    This function modifies ``item`` in place, mutating the measurement results and
    popping the arrays that store the bitflips.
    """
    flip_keys = [key for key in item.keys() if key.startswith(TWIRLING_PREFIX)]

    for flip_key in flip_keys:
        target_key = flip_key[len(TWIRLING_PREFIX) :]

        # Validate that target key exists
        if target_key not in item:
            raise ValueError(
                f"Measurement flip key '{flip_key}' references non-existent "
                f"register '{target_key}'. Available registers: {list(item.keys())}"
            )

        # Apply XOR and remove flip key
        flip_data = item.pop(flip_key)
        item[target_key] ^= flip_data


def flatten_twirling_axes(item: QuantumProgramItemResult, pub_shape: tuple[int, ...]) -> None:
    """Flatten the leading ``num_randomizations`` axis into the shots axis in-place.

    When twirling is enabled, the executor returns measurement data with shape
    ``(num_rand, *pub_shape, shots_per_rand, num_bits)``. This function reshapes
    each array to ``(*pub_shape, total_shots, num_bits)`` where
    ``total_shots = num_rand * shots_per_rand``.

    The function should only be called when twirling was on.

    Args:
        item: Dictionary mapping classical register names to measurement arrays.
            Modified in-place.
        pub_shape: The parameter-sweep shape of the pub (without the leading
            ``num_rand`` axis), e.g. ``()`` for a non-parametric pub or
            ``(3,)`` for a 1-D parameter sweep.
    """
    for creg_name, data in list(item.items()):
        num_rand = data.shape[0]
        shots_per_rand = data.shape[len(pub_shape) + 1]
        total_shots = num_rand * shots_per_rand
        num_bits = data.shape[-1]
        # Move num_rand axis to be adjacent to shots_per_rand before reshaping
        # to avoid mixing randomization indices with parameter sweep indices
        data_reordered = np.moveaxis(data, 0, len(pub_shape))
        # Now shape is (*pub_shape, num_rand, shots_per_rand, num_bits) and is safe for reshaping
        item[creg_name] = data_reordered.reshape(*pub_shape, total_shots, num_bits)
