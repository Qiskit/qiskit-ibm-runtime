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

from __future__ import annotations

from typing import TYPE_CHECKING

from .noise_learner_result import LayerError, NoiseLearnerResult, PauliLindbladError
from .result_decoder import ResultDecoder

if TYPE_CHECKING:
    from qiskit_ibm_runtime.noise_learner_v3.noise_learner_v3_result import NoiseLearnerV3Results


class NoiseLearnerResultDecoder(ResultDecoder):
    """Class used to decode noise learner results"""

    @classmethod
    def decode(cls, raw_result: str) -> NoiseLearnerResult | NoiseLearnerV3Results:
        """Convert the result to NoiseLearnerResult."""
        if "schema_version" in raw_result:
            # pylint: disable=import-outside-toplevel
            from qiskit_ibm_runtime.noise_learner_v3.noise_learner_v3_decoders import (
                NoiseLearnerV3ResultDecoder,
            )

            return NoiseLearnerV3ResultDecoder().decode(raw_result)

        # Decode for legacy noise learner
        decoded: dict = super().decode(raw_result)

        data = []
        for layer in decoded["data"]:
            if isinstance(layer, LayerError):
                data.append(layer)
            else:
                # supports the legacy result format
                error = PauliLindbladError(layer[1]["generators"], layer[1]["rates"])
                datum = LayerError(layer[0]["circuit"], layer[0]["qubits"], error)
                data.append(datum)

        return NoiseLearnerResult(data=data, metadata=decoded["metadata"])
