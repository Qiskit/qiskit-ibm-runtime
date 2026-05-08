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

"""Constant values."""

from collections.abc import Sequence

from .decoders.quantum_program import QuantumProgramResultDecoder
from .decoders.executor_sampler.decoder import ExecutorSamplerResultDecoder
from .decoders.result_decoder import ResultDecoder
from .decoders.noise_learner import NoiseLearnerResultDecoder
from .decoders.noise_learner_v3.decoder import NoiseLearnerV3ResultDecoder
from .decoders.runner import RunnerResult


DEFAULT_DECODERS: dict[str, type[ResultDecoder] | Sequence[type[ResultDecoder]]] = {
    "sampler": ResultDecoder,
    "estimator": ResultDecoder,
    "executor": [QuantumProgramResultDecoder, ExecutorSamplerResultDecoder],
    "noise-learner": [NoiseLearnerResultDecoder, NoiseLearnerV3ResultDecoder],
    "circuit-runner": RunnerResult,
    "qasm3-runner": RunnerResult,
}
