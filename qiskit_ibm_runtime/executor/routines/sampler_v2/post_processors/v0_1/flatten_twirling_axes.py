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

from ......quantum_program.quantum_program_result import QuantumProgramItemResult


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
