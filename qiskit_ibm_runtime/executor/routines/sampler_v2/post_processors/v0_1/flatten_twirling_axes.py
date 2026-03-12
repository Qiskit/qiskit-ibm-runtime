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

"""Function for flattening the results when twirling was applied."""

from __future__ import annotations

import numpy as np


def flatten_twirling_axes(item: dict[str, np.ndarray], pub_shape: tuple[int, ...]) -> None:
    """Flatten the leading num_randomizations axis into the shots axis in-place.

    When twirling is enabled, the executor returns measurement data with shape
    ``(num_rand, *pub_shape, shots_per_rand, num_bits)``. This function reshapes
    each array to ``(*pub_shape, total_shots, num_bits)`` where
    ``total_shots = num_rand * shots_per_rand``.

    If the data does not have the expected twirled shape (i.e. its ndim equals
    ``len(pub_shape) + 2`` rather than ``len(pub_shape) + 3``), it is left
    unchanged.

    Args:
        item: Dictionary mapping classical register names to measurement arrays.
            Modified in-place.
        pub_shape: The parameter-sweep shape of the pub (without the leading
            ``num_rand`` axis), e.g. ``()`` for a non-parametric pub or
            ``(3,)`` for a 1-D parameter sweep.

    Raises:
        ValueError: If the data has the expected twirled ndim but the middle
            dimensions do not match ``pub_shape``.
    """
    # NOTE: This assumes a single num_randomization axis, which is the existing practice.
    # In theory, one could set more than one such axes.
    expected_non_twirled_ndim = len(pub_shape) + 2  # (*pub_shape, shots, bits)
    for creg_name, data in list(item.items()):
        if data.ndim == expected_non_twirled_ndim + 1:
            # Twirled shape: (num_rand, *pub_shape, shots_per_rand, num_bits)
            # Validate that the middle dimensions match pub_shape
            actual_pub_shape = data.shape[1 : 1 + len(pub_shape)]
            if actual_pub_shape != pub_shape:
                raise ValueError(
                    f"Classical register '{creg_name}': expected pub shape {pub_shape} "
                    f"in dimensions [1:{1 + len(pub_shape)}] of data with shape {data.shape}, "
                    f"but found {actual_pub_shape}."
                )
            num_rand = data.shape[0]
            shots_per_rand = data.shape[len(pub_shape) + 1]
            total_shots = num_rand * shots_per_rand
            num_bits = data.shape[-1]
            # Move num_rand axis to be adjacent to shots_per_rand before reshaping
            # to avoid mixing randomization indices with parameter sweep indices
            data_reordered = np.moveaxis(data, 0, len(pub_shape))
            # Now shape is (*pub_shape, num_rand, shots_per_rand, num_bits)
            item[creg_name] = data_reordered.reshape(*pub_shape, total_shots, num_bits)
        # else: already the correct non-twirled shape — no reshape needed
