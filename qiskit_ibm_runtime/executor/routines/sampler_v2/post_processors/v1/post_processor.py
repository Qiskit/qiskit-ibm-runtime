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

"""Post-processing functions for converting QuantumProgramResult to primitive-specific formats."""

from __future__ import annotations
from typing import cast

import numpy as np
from qiskit.primitives import PrimitiveResult

from ......quantum_program.quantum_program_result import QuantumProgramResult
from ...sampler import SamplerV2
from ....options.sampler_options import SamplerOptions
from ..utils import register_post_processor
from .executor_metadata_to_sampler_metadata import executor_metadata_to_sampler_metadata


def _flatten_twirling_axes(item: dict[str, np.ndarray], pub_shape: tuple[int, ...]) -> None:
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
            item[creg_name] = data.reshape(*pub_shape, total_shots, num_bits)
        # else: already the correct non-twirled shape — no reshape needed


@register_post_processor("v1")
def sampler_v2_post_processor_v1(result: QuantumProgramResult) -> PrimitiveResult:
    """Convert QuantumProgramResult to SamplerV2 PrimitiveResult.

    This function transforms the raw quantum program execution results into the
    format expected by SamplerV2, creating BitArray objects and SamplerPubResult
    containers for each pub.

    When twirling is enabled, the executor returns measurement data with a leading
    ``num_randomizations`` axis. This function flattens that axis together with the
    ``shots_per_randomization`` axis into a single ``total_shots`` axis.

    Flattening is performed when twirling is enabled (determined by checking the
    ``options`` field in ``result.passthrough_data["post_processor"]``). The
    ``pub_shapes`` field provides the parameter sweep shape for each pub.

    Args:
        result: The raw quantum program result containing measurement data.

    Returns:
        PrimitiveResult containing SamplerPubResult objects.
    """

    # Apply measurement twirling bit flips
    prefix = "measurement_flips."
    for item in result:
        for key in list(item.keys()):
            if key.startswith(prefix):
                item[key[len(prefix) :]] ^= item.pop(key)
    # TODO: This could fail if the user manually specifies a register starting with the prefix.

    if not isinstance(result.passthrough_data, dict):
        raise ValueError(
            "Wrong type for passthrough data: Expected a 'dict', found "
            f"'{type(result.passthrough_data)}'."
        )

    passthrough = cast(dict, result.passthrough_data or {})
    if (post_processor_data := passthrough.get("post_processor", None)) is None:
        raise ValueError("Missing 'post_processor'.")
    if (options_dict := post_processor_data.get("options", None)) is None:
        raise ValueError("Missing 'options'.")
    if (pub_shapes := post_processor_data.get("pub_shapes", None)) is None:
        raise ValueError("Missing 'pub_shapes'.")
    if len(pub_shapes) != len(result):
        raise ValueError(f"Expected 'pub_shape' of lenght {len(result)}, found {len(pub_shapes)}.")

    try:
        options = SamplerOptions(**options_dict)
    except (TypeError, ValueError) as ex:
        raise ValueError("Couldn't initialize SamplerOptions from 'options_dict'.") from ex

    if options.twirling.enable_gates or options.twirling.enable_measure:
        for item, shape in zip(result, pub_shapes):
            _flatten_twirling_axes(item, tuple(shape))

    # Compute the shots from the second-to-last axis of the result arrays
    shots = next(iter({array.shape[-2] for array in result[0].values()}))
    metadata = executor_metadata_to_sampler_metadata(result.metadata, options, pub_shapes, shots)

    sampler_result = SamplerV2.quantum_program_result_to_primitive_result(result, metadata)
    return sampler_result
