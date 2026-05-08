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

"""Decoders for quantum programs."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from ..result_decoder import ResultDecoder

from .post_processor_v0_1 import sampler_v2_post_processor_v0_1

if TYPE_CHECKING:
    from qiskit.primitives.containers import PrimitiveResult

    from ...results.quantum_program import QuantumProgramResult

logger = logging.getLogger(__name__)

SAMPLER_POST_PROCESSORS = {
    "v0.1": sampler_v2_post_processor_v0_1,
}


class ExecutorSamplerResultDecoder(ResultDecoder):
    """Decoder for ExecutorSampler results (from QuantumProgramResult)."""

    @classmethod
    def decode(cls, raw_result: QuantumProgramResult) -> QuantumProgramResult | PrimitiveResult:
        """Apply post-processing to the decoded result.

        Post-processing is only applied if ``result._semantic_role`` has a supported value.
        Otherwise, the result is returned unchanged.

        Args:
            raw_result: The decoded result.

        Returns:
            Post-processed result or original result if no post-processing applies.
        """
        if not (semantic_role := raw_result._semantic_role):
            return raw_result

        if semantic_role == "sampler_v2":
            # TODO: Circular import issue. Consider changing file structure.

            if not isinstance(raw_result.passthrough_data, dict):
                raise ValueError("Expected passthrough data to be of dict-like format.")

            try:
                version = raw_result.passthrough_data.get("post_processor", {})["version"]
            except KeyError:
                raise ValueError("Could not determine a post-processor version.")

            try:
                post_processor_fn = SAMPLER_POST_PROCESSORS[version]
            except KeyError:
                raise ValueError(f"No post-processor found for version {version}.")

            return post_processor_fn(raw_result)

        return raw_result
