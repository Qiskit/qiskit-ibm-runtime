# This code is part of Qiskit.
#
# (C) Copyright IBM 2021-2026.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Circuit-runner decoder."""

from __future__ import annotations

from ..results.runner import RunnerResult
from .result_decoder import ResultDecoder


class RunnerResultDecoder(ResultDecoder):
    """Result class for IBM Quantum Compute program circuit-runner."""

    @classmethod
    def decode(cls, data: str) -> RunnerResult:
        """Decoding for results from IBM Quantum Compute jobs."""
        return RunnerResult.from_dict(super().decode(data))
