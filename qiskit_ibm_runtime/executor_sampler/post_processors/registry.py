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

"""Utility functions for post-processors."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

    from qiskit.primitives import PrimitiveResult

    from ...quantum_program.quantum_program_result import QuantumProgramResult

    # Type alias for sampler post-processor functions
    PostProcessorFunc = Callable[[QuantumProgramResult], PrimitiveResult]

# Registry for sampler post-processing functions
SAMPLER_POST_PROCESSORS: dict[str, PostProcessorFunc] = {}


def register_post_processor(name: str) -> Callable[[PostProcessorFunc], PostProcessorFunc]:
    """Decorator to register post-processing functions.

    Args:
        name: Unique identifier for the post-processor

    Returns:
        Decorator function.
    """

    def decorator(func: PostProcessorFunc) -> PostProcessorFunc:
        SAMPLER_POST_PROCESSORS[name] = func
        return func

    return decorator
