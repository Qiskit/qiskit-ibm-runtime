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

from .result_decoder import ResultDecoder


class ExecutorResultDecoder(ResultDecoder):
    """Class used to decode noise learner results"""

    @classmethod
    def decode(cls, raw_result: str):  # type: ignore # pylint: disable=arguments-differ
        """Convert the result to QuantumProgramResult."""
        # pylint: disable=import-outside-toplevel
        from qiskit_ibm_runtime.quantum_program.quantum_program_decoders import (
            QuantumProgramResultDecoder,
        )

        return QuantumProgramResultDecoder().decode(raw_result)
