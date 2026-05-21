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

from .decoders.quantum_program.decoder import QuantumProgramResultDecoder
from .utils.result_decoder import ResultDecoder
from .decoders.noise_learner import NoiseLearnerResultDecoder
from .utils.runner_result import RunnerResult


DEFAULT_DECODERS: dict[str, type[ResultDecoder] | list[type[ResultDecoder]]] = {
    "sampler": ResultDecoder,
    "estimator": ResultDecoder,
    "executor": QuantumProgramResultDecoder,
    "noise-learner": NoiseLearnerResultDecoder,
    "circuit-runner": RunnerResult,
    "qasm3-runner": RunnerResult,
}
