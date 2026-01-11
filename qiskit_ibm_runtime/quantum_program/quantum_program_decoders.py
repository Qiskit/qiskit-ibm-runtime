# This code is part of Qiskit.
#
# (C) Copyright IBM 2025.
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

from ibm_quantum_schemas.models.executor.version_0_1.models import (
    QuantumProgramResultModel as QuantumProgramResultModel_0_1,
)

# pylint: disable=unused-import,cyclic-import
from ..utils.result_decoder import ResultDecoder
from .converters import quantum_program_result_from_0_1

logger = logging.getLogger(__name__)

AVAILABLE_DECODERS = {"v0.1": (quantum_program_result_from_0_1, QuantumProgramResultModel_0_1)}


class QuantumProgramResultDecoder(ResultDecoder):
    """Decoder for quantum program results."""

    @classmethod
    def decode(cls, raw_result: str):  # type: ignore[no-untyped-def]
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
