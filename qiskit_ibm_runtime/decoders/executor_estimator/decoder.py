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

"""Result decoder for client-side estimator."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from ..executor.decoder import BaseClientSideResultDecoder
from .post_processor_v0_1 import estimator_v2_post_processor_v0_1

if TYPE_CHECKING:
    from qiskit.primitives.containers import PrimitiveResult

    from ...results.quantum_program import QuantumProgramResult

logger = logging.getLogger(__name__)


class ClientSideEstimatorDecoder(BaseClientSideResultDecoder):
    """Decoder for quantum program results."""

    SEMANTIC_ROLE = "estimator_v2"

    SUPPORTED_POST_PROCESSORS = {
        "v0.1": estimator_v2_post_processor_v0_1,
    }

    @classmethod
    def decode(cls, result: QuantumProgramResult) -> PrimitiveResult:
        """Decode a QuantumProgramResult into the result type."""
        return super().decode(result)
