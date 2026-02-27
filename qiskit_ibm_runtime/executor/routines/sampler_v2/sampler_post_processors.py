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

from collections.abc import Callable

from qiskit.primitives import PrimitiveResult

from ....quantum_program.quantum_program_result import QuantumProgramResult
from .sampler import SamplerV2

# Type alias for sampler post-processor functions
PostProcessorFunc = Callable[[QuantumProgramResult], PrimitiveResult]

# Registry for sampler post-processing functions
SAMPLER_POST_PROCESSORS: dict[str, PostProcessorFunc] = {}


def register_post_processor(name: str) -> Callable[[PostProcessorFunc], PostProcessorFunc]:
    """Decorator to register post-processing functions.

    Args:
        name: Unique identifier for the post-processor

    Returns:
        Decorator function
    """

    def decorator(func: PostProcessorFunc) -> PostProcessorFunc:
        SAMPLER_POST_PROCESSORS[name] = func
        return func

    return decorator


@register_post_processor("v1")
def sampler_v2_post_processor_v1(result: QuantumProgramResult) -> PrimitiveResult:
    """Convert QuantumProgramResult to SamplerV2 PrimitiveResult.

    This function transforms the raw quantum program execution results into the
    format expected by SamplerV2, creating BitArray objects and SamplerPubResult
    containers for each pub.

    Args:
        result: The raw quantum program result containing measurement data.

    Returns:
        PrimitiveResult containing SamplerPubResult objects.
    """

    # In the future post processing will happen here. (For example, measurement twirling)

    return SamplerV2.quantum_program_result_to_primitive_result(result)
