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

"""Result decoder for calibrator."""

from __future__ import annotations

import logging
from typing import Any

from ibm_quantum_schemas.calibrator.version_0_1 import (
    CalibratorResultModel as CalibratorResultModel_0_1,
)

from ...results import CalibratorResult
from ..result_decoder import ResultDecoder
from .converters import calibrator_result_from_0_1

logger = logging.getLogger(__name__)

AVAILABLE_DECODERS = {
    "v0.1": (calibrator_result_from_0_1, CalibratorResultModel_0_1),
}


class CalibratorResultDecoder(ResultDecoder):
    """Decoder for Executor results."""

    @classmethod
    def is_applicable(cls, data: Any) -> bool:
        """Return `True` if this decoder can be applied."""
        if isinstance(data, CalibratorResult):
            return False
        return True

    @classmethod
    def decode(cls, raw_result: str) -> CalibratorResult:
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
