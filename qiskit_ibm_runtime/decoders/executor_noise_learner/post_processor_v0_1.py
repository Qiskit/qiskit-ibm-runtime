# This code is part of Qiskit.
#
# (C) Copyright IBM 2026.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Post-processing for the client-side NoiseLearner: delegates to qiskit-noise-learning."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from qiskit.quantum_info import PauliLindbladMap

    from ...results.quantum_program import QuantumProgramResult

from ...results.noise_learner_v3 import NoiseLearnerV3Result

logger = logging.getLogger(__name__)


# TODO: replace this with qiskit-noise-learning
def post_process(result: QuantumProgramResult) -> dict[str, PauliLindbladMap]:
    """Process the results and return a :class:`.Fit` object.

    Note: the fit contains all of the data through the analysis pipeline. The dict mapping gate
    names to fit PauliLindbladMaps can be retrieved from this. (There should be just one function
    for this, but currently requires a few lines of code).
    """
    return {}


def noise_learner_v3_post_processor_v0_1(result: QuantumProgramResult) -> NoiseLearnerV3Result:
    """Convert a quantum program result to a noise learner result for NoiseLearnerV3.

    Args:
        result: The raw quantum program result.

    Returns:
        A :class:`~qiskit_ibm_runtime.results.NoiseLearnerV3Result`.
    """
    if len(result) == 0:
        return NoiseLearnerV3Result()

    return NoiseLearnerV3Result()  # TODO: handle the results
