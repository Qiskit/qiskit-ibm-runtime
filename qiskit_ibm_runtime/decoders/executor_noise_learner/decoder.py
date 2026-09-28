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

from ..quantum_program.decoder import BaseClientSideResultDecoder
from .post_processor_v0_1 import noise_learner_v3_post_processor_v0_1

if TYPE_CHECKING:
    from ...results.noise_learner_v3 import NoiseLearnerV3Result
    from ...results.quantum_program import QuantumProgramResult


logger = logging.getLogger(__name__)

class ClientSideNoiseLearnerResultDecoder(BaseClientSideResultDecoder):
    """Decoder for quantum program results."""
    
    SEMANTIC_ROLE = "noise_learner_v3"

    SUPPORTED_POST_PROCESSORS = {
        "v0.1": noise_learner_v3_post_processor_v0_1,
    }

    @classmethod
    def decode(cls, result: QuantumProgramResult) -> NoiseLearnerV3Result:
        """Decode a QuantumProgramResult into the result type."""
        return super().decode(result)

