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

from typing import Any
from collections.abc import Callable

from qiskit.primitives import PrimitiveResult
from qiskit.primitives.containers import BitArray, DataBin, SamplerPubResult

from .quantum_program_result import QuantumProgramResult

# Type alias for post-processor functions
PostProcessorFunc = Callable[[QuantumProgramResult, dict[str, Any]], Any]

# Registry for post-processing functions
POST_PROCESSORS: dict[str, PostProcessorFunc] = {}


def register_post_processor(name: str) -> Callable[[PostProcessorFunc], PostProcessorFunc]:
    """Decorator to register post-processing functions.

    Args:
        name: Unique identifier for the post-processor

    Returns:
        Decorator function

    Example:
        .. code-block:: python

            @register_post_processor("quantum_program_result_to_sampler_v2")
            def my_processor(qp_result, metadata):
                ...
    """

    def decorator(func: PostProcessorFunc) -> PostProcessorFunc:
        POST_PROCESSORS[name] = func
        return func

    return decorator


@register_post_processor("quantum_program_result_to_sampler_v2")
def quantum_program_result_to_sampler_v2(
    qp_result: QuantumProgramResult, metadata: dict[str, Any]
) -> PrimitiveResult:
    """Convert QuantumProgramResult to SamplerV2 PrimitiveResult.

    This function transforms the raw quantum program execution results into the
    format expected by SamplerV2, creating BitArray objects and SamplerPubResult
    containers for each pub.

    Args:
        qp_result: The raw quantum program result containing measurement data.
            Each item in qp_result is a dictionary where keys are classical
            register names and values are numpy arrays of measurement data.
        metadata: Additional metadata (currently unused, reserved for future use).

    Returns:
        PrimitiveResult containing SamplerPubResult objects with BitArray data

    Raises:
        ValueError: If data is malformed or inconsistent
    """
    # Build SamplerPubResult for each pub
    pub_results = []
    for idx, item_data in enumerate(qp_result):
        # Validate that measurement data exists
        if not item_data:
            raise ValueError(f"Pub {idx} has no measurement data")

        # Infer pub_shape from the first classical register's data
        # meas_data shape: (...pub_shape..., num_shots, num_bits)
        first_meas_data = next(iter(item_data.values()))
        pub_shape = first_meas_data.shape[:-2]

        # Create BitArray for each classical register found in the data
        bit_arrays = {}
        for creg_name, meas_data in item_data.items():
            # Create BitArray from measurement data (bit array format)
            # meas_data shape: (..., num_shots, num_clbits)
            bit_array = BitArray.from_bool_array(meas_data)
            bit_arrays[creg_name] = bit_array

        data_bin = DataBin(**bit_arrays, shape=pub_shape)

        pub_result = SamplerPubResult(data=data_bin, metadata={})
        pub_results.append(pub_result)

    # Create and return PrimitiveResult with preserved metadata
    return PrimitiveResult(pub_results, metadata={"quantum_program_metadata": qp_result.metadata})
