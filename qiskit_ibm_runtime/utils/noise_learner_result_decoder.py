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

from typing import Dict

from .noise_learner_result import NoiseLearnerDatum, NoiseLearnerResult
from .result_decoder import ResultDecoder


class NoiseLearnerResultDecoder(ResultDecoder):
    """Class used to decode noise learner results"""

    @classmethod
    def decode(  # type: ignore # pylint: disable=arguments-differ
        cls, raw_result: str
    ) -> NoiseLearnerResult:
        """Convert the result to NoiseLearnerResult."""
        decoded: Dict = super().decode(raw_result)

        data = []
        for layer in decoded["data"]:
            datum = NoiseLearnerDatum(
                layer[0]["circuit"], layer[0]["qubits"], layer[1]["generators"], layer[1]["rates"]
            )
            data.append(datum)

        return NoiseLearnerResult(data=data, metadata=decoded["metadata"])
