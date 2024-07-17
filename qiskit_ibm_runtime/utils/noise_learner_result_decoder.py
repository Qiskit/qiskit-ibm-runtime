# This code is part of Qiskit.
#
# (C) Copyright IBM 2024.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""NoiseLearner result decoder."""

from typing import Dict, Union
import numpy as np

from qiskit.primitives.containers import PrimitiveResult

from .noise_learner_result import NoiseLearnerResult
from .result_decoder import ResultDecoder


class NoiseLearnerResultDecoder(ResultDecoder):
    """Class used to decode noise learner results"""

    @classmethod
    def decode(  # type: ignore # pylint: disable=arguments-differ
        cls, raw_result: str
    ) -> Union[NoiseLearnerResult, PrimitiveResult]:
        """Convert the result to EstimatorResult."""
        decoded: Dict = super().decode(raw_result)
        if isinstance(decoded, PrimitiveResult):
            return decoded
        else:
            return NoiseLearnerResult(
                data=decoded["data"],
                metadata=decoded["metadata"],
            )
