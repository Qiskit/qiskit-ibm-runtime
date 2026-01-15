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

"""Noise learner program."""

from __future__ import annotations

from typing import Any
import logging

from ibm_quantum_schemas.models.noise_learner_v3.version_0_1.models import (
    NoiseLearnerV3ResultsModel as NoiseLearnerV3ResultsModel_0_1,
)

from qiskit_ibm_runtime.noise_learner_v3.noise_learner_v3_result import (  # type: ignore[attr-defined]
    NoiseLearnerV3Results,
)

# pylint: disable=unused-import,cyclic-import
from ..utils.result_decoder import ResultDecoder
from .converters.version_0_1 import noise_learner_v3_result_from_0_1

logger = logging.getLogger(__name__)

AVAILABLE_DECODERS = {"v0.1": (noise_learner_v3_result_from_0_1, NoiseLearnerV3ResultsModel_0_1)}


class NoiseLearnerV3ResultDecoder(ResultDecoder):
    """Decoder for noise learner V3."""

    @classmethod
    def decode(cls, raw_result: str) -> NoiseLearnerV3Results:  # type: ignore[no-untyped-def]
        """Decode raw json to result type."""
        decoded: dict[str, Any] = super().decode(raw_result)

        try:
            schema_version = decoded["schema_version"]
        except KeyError:
            raise ValueError("Missing schema version.")

        try:
            decoder, model = AVAILABLE_DECODERS[schema_version]
        except KeyError:
            raise ValueError(f"No decoder found for schema version {schema_version}.")

        return decoder(model.model_validate_json(raw_result))
