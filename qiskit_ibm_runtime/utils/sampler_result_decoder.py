# This code is part of Qiskit.
#
# (C) Copyright IBM 2022.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Sampler result decoder."""

from typing import Dict

from qiskit.primitives import PrimitiveResult

from .result_decoder import ResultDecoder


class SamplerResultDecoder(ResultDecoder):
    """Class used to decode sampler results."""

    @classmethod
    def decode(cls, raw_result: str) -> PrimitiveResult:
        """Convert the result to SamplerResult."""
        decoded: Dict = super().decode(raw_result)

        return decoded

        # TODO: Handle V2 result that is returned in dict format
