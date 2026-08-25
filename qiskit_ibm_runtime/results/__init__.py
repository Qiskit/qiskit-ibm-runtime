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

"""
==================================================
Result classes (:mod:`qiskit_ibm_runtime.results`)
==================================================

.. autosummary::
   :toctree: ../stubs/
   :nosignatures:

   EstimatorPubResult
   LayerError
   PauliLindbladError
   NoiseLearnerResult
   NoiseLearnerV3Result
   NoiseLearnerV3Results
   ItemMetadata
   QuantumProgramResult
   QuantumProgramItemResult
   ChunkPart
   ChunkSpan
   ChunkTiming
   ItemMetadata
   Metadata
   Metadata
   SchedulerTiming
   StretchValues
"""  # noqa: D205, D212, D415

from ..utils.deprecation import issue_deprecation_msg
from .estimator_pub import EstimatorPubResult
from .noise_learner import LayerError, NoiseLearnerResult, PauliLindbladError
from .noise_learner_v3 import NoiseLearnerV3Result, NoiseLearnerV3Results
from .quantum_program import (
    ItemMetadata,
    Metadata,
    QuantumProgramItemResult,
    QuantumProgramResult,
    SchedulerTiming,
    StretchValues,
)

_DEPRECATED_NAMES = frozenset({"ChunkPart", "ChunkSpan", "ChunkTiming"})


def __getattr__(name: str) -> object:
    if name in _DEPRECATED_NAMES:
        import samplomatic.quantum_program as _sq

        issue_deprecation_msg(
            msg=f"Importing '{name}' from 'qiskit_ibm_runtime.results' is deprecated",
            version="0.50.0",
            remedy=f"Import '{name}' from 'samplomatic.quantum_program' instead.",
            stacklevel=2,
        )
        return getattr(_sq, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
