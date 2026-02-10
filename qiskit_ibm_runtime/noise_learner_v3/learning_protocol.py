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

"""Learning protocols."""

from enum import Enum
from typing import Literal


class LearningProtocol(str, Enum):
    """The supported learning protocols."""

    PAULI_LINDBLAD = "pauli_lindblad"
    """Pauli Lindblad learning from arXiv:2201.09866."""

    TREX = "trex"
    """Readout learning protocol."""


LearningProtocolLiteral = LearningProtocol | Literal["pauli_lindblad", "trex"]
"""The supported learning protocols.
 * ``pauli_lindblad``: Pauli Lindblad learning from arXiv:2201.09866..
 * ``trex``: Readout learning protocol.
"""
