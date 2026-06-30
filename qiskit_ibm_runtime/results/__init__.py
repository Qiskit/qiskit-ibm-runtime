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

from .estimator_pub import EstimatorPubResult
from .noise_learner import LayerError, NoiseLearnerResult, PauliLindbladError
from .noise_learner_v3 import NoiseLearnerV3Result, NoiseLearnerV3Results
from .quantum_program import (
    ChunkPart,
    ChunkSpan,
    ChunkTiming,
    ItemMetadata,
    Metadata,
    QuantumProgramItemResult,
    QuantumProgramResult,
    SchedulerTiming,
    StretchValues,
)
