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

import logging
from typing import Dict

# pylint: disable=unused-import,cyclic-import
from ..utils.result_decoder import ResultDecoder
from .converters.version_0_1 import noise_learner_v3_result_from_0_1

logger = logging.getLogger(__name__)

AVAILABLE_DECODERS = {"v0.1": noise_learner_v3_result_from_0_1}


class NoiseLearnerV3ResultDecoder(ResultDecoder):
    @classmethod
    def decode(cls, raw_result: str):
        """Decode raw json to result type."""
        decoded: Dict = super().decode(raw_result)

        try:
            schema_version = decoded["schema_version"]
        except KeyError:
            raise ValueError("Missing schema version.")

        try:
            decoder = AVAILABLE_DECODERS[schema_version]
        except KeyError:
            raise ValueError(f"No decoder found for schema version {schema_version}.")

        return decoder(decoded)
