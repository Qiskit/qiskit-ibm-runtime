# This code is part of Qiskit.
#
# (C) Copyright IBM 2025-2026.
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

from ibm_quantum_schemas.executor.version_0_1 import (
    QuantumProgramResultModel as QuantumProgramResultModel_0_1,
)
from ibm_quantum_schemas.executor.version_0_2 import (
    QuantumProgramResultModel as QuantumProgramResultModel_0_2,
)
from ibm_quantum_schemas.executor.version_1_0 import (
    QuantumProgramResultModel as QuantumProgramResultModel_1_0,
)

from ...utils.result_decoder import ResultDecoder
from .converters import (
    quantum_program_result_from_0_1,
    quantum_program_result_from_0_2,
    quantum_program_result_from_1_0,
)

if TYPE_CHECKING:
    from qiskit.primitives.containers import PrimitiveResult

    from ...results.quantum_program import QuantumProgramResult

logger = logging.getLogger(__name__)

AVAILABLE_DECODERS = {
    "v0.1": (quantum_program_result_from_0_1, QuantumProgramResultModel_0_1),
    "v0.2": (quantum_program_result_from_0_2, QuantumProgramResultModel_0_2),
    "v1.0": (quantum_program_result_from_1_0, QuantumProgramResultModel_1_0),
}


class QuantumProgramResultDecoder(ResultDecoder):
    """Decoder for quantum program results."""

    @classmethod
    def decode(cls, raw_result: str) -> QuantumProgramResult | PrimitiveResult:
        """Decode raw json to result type."""
        decoded: dict[str, str] = super().decode(raw_result)

        try:
            schema_version = decoded["schema_version"]
        except KeyError:
            raise ValueError("Missing schema version.")

        try:
            decoder, model = AVAILABLE_DECODERS[schema_version]
        except KeyError:
            raise ValueError(f"No decoder found for schema version {schema_version}.")

        quantum_program_result = decoder(model.model_validate_json(raw_result))
        return cls._apply_post_processing(quantum_program_result)

    @staticmethod
    def _apply_post_processing(
        result: QuantumProgramResult,
    ) -> QuantumProgramResult | PrimitiveResult:
        """Apply post-processing to the decoded result.

        Post-processing is only applied if ``result._semantic_role`` has a supported value.
        Otherwise, the result is returned unchanged.

        Args:
            result: The decoded result.

        Returns:
            Post-processed result or original result if no post-processing applies.
        """
        if not (semantic_role := result._semantic_role):
            return result

        if semantic_role == "sampler_v2":
            # TODO: Circular import issue. Consider changing file structure.
            from ..executor_sampler.post_processor_v0_1 import (
                sampler_v2_post_processor_v0_1,
            )

            SAMPLER_POST_PROCESSORS = {
                "v0.1": sampler_v2_post_processor_v0_1,
            }

            if not isinstance(result.passthrough_data, dict):
                raise ValueError("Expected passthrough data to be of dict-like format.")

            try:
                version = result.passthrough_data.get("post_processor", {})["version"]
            except KeyError:
                raise ValueError("Could not determine a post-processor version.")

            try:
                post_processor_fn = SAMPLER_POST_PROCESSORS[version]
            except KeyError:
                raise ValueError(f"No post-processor found for version {version}.")

            return post_processor_fn(result)

        return result
