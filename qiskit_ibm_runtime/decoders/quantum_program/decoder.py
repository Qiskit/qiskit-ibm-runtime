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
from typing import TYPE_CHECKING, Any

from ibm_quantum_schemas.executor.version_0_1 import (
    QuantumProgramResultModel as QuantumProgramResultModel_0_1,
)
from ibm_quantum_schemas.executor.version_0_2 import (
    QuantumProgramResultModel as QuantumProgramResultModel_0_2,
)
from ibm_quantum_schemas.executor.version_1_0 import (
    QuantumProgramResultModel as QuantumProgramResultModel_1_0,
)
from ibm_quantum_schemas.executor.version_1_1 import (
    QuantumProgramResultModel as QuantumProgramResultModel_1_1,
)
from ibm_quantum_schemas.executor.version_2_0 import (
    QuantumProgramResultModel as QuantumProgramResultModel_2_0,
)

from ...results.quantum_program import QuantumProgramResult
from ..result_decoder import ResultDecoder
from .converters import (
    quantum_program_result_from_0_1,
    quantum_program_result_from_0_2,
    quantum_program_result_from_1_0,
    quantum_program_result_from_1_1,
    quantum_program_result_from_2_0,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from qiskit.primitives.containers import PrimitiveResult

    from ...results.noise_learner_v3 import NoiseLearnerV3Result

logger = logging.getLogger(__name__)

AVAILABLE_DECODERS = {
    "v0.1": (quantum_program_result_from_0_1, QuantumProgramResultModel_0_1),
    "v0.2": (quantum_program_result_from_0_2, QuantumProgramResultModel_0_2),
    "v1.0": (quantum_program_result_from_1_0, QuantumProgramResultModel_1_0),
    "v1.1": (quantum_program_result_from_1_1, QuantumProgramResultModel_1_1),
    "v2.0": (quantum_program_result_from_2_0, QuantumProgramResultModel_2_0),
}


class QuantumProgramResultDecoder(ResultDecoder):
    """Decoder for quantum program results."""

    @classmethod
    def decode(
        cls, raw_result: str
    ) -> QuantumProgramResult | PrimitiveResult | NoiseLearnerV3Result:
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

        return decoder(model.model_validate_json(raw_result))


class BaseClientSideResultDecoder(ResultDecoder):
    """Base class for client-side primitives decoders."""

    SEMANTIC_ROLE: str
    """The semantic tole for this decoder."""

    SUPPORTED_POST_PROCESSORS: dict[str, Callable]
    """The available post processors.

    This is a dictionary mapping between versions and functions.
    """

    @classmethod
    def is_applicable(cls, data: Any) -> bool:
        """Return `True` if this decoder can be applied."""
        if not isinstance(data, QuantumProgramResult):
            return False

        if not (semantic_role := data._semantic_role):
            return False
        else:
            return semantic_role == cls.SEMANTIC_ROLE

    @classmethod
    def decode(cls, result: QuantumProgramResult) -> PrimitiveResult | NoiseLearnerV3Result:
        """Decode a QuantumProgramResult into the result type."""
        if not isinstance(result.passthrough_data, dict):
            raise ValueError("Expected passthrough data to be of dict-like format.")

        try:
            version: str = result.passthrough_data.get("post_processor", {})["version"]
        except KeyError:
            raise ValueError("Could not determine a post-processor version.")

        try:
            post_processor_fn = cls.SUPPORTED_POST_PROCESSORS[version]
        except KeyError:
            raise ValueError(f"No post-processor found for {cls.SEMANTIC_ROLE} version {version}.")

        return post_processor_fn(result)
