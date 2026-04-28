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

"""Converters for NLV3 params."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import NamedTuple, TYPE_CHECKING

from ibm_quantum_schemas.common import BaseParamsModel
from ibm_quantum_schemas.noise_learner_v3.version_0_1 import ParamsModel as ParamsModel_0_1
from ibm_quantum_schemas.noise_learner_v3.version_0_2 import ParamsModel as ParamsModel_0_2


from .converters import (
    noise_learner_v3_inputs_from_0_1,
    noise_learner_v3_inputs_to_0_1,
    noise_learner_v3_inputs_from_0_2,
    noise_learner_v3_inputs_to_0_2,
)

if TYPE_CHECKING:
    from qiskit.circuit import CircuitInstruction
    from qiskit_ibm_runtime.options import NoiseLearnerV3Options


class ParamsConverter(NamedTuple):
    """A helper to store params models and converters."""

    model: type[BaseParamsModel]
    """The model describing the NLV3 inputs, or 'params'."""

    decoder: Callable[[BaseParamsModel], tuple[list[CircuitInstruction], NoiseLearnerV3Options]]
    """A function to decode the inputs of NLV3."""

    encoder: Callable[[Iterable[CircuitInstruction], NoiseLearnerV3Options], BaseParamsModel]
    """A function to encode the inputs of NLV3."""


NOISE_LEARNER_V3_PARAMS_CONVERTERS = {
    "v0.1": ParamsConverter(
        ParamsModel_0_1, noise_learner_v3_inputs_from_0_1, noise_learner_v3_inputs_to_0_1
    ),
    "v0.2": ParamsConverter(
        ParamsModel_0_2, noise_learner_v3_inputs_from_0_2, noise_learner_v3_inputs_to_0_2
    ),
}
"""Converter to/from schema model for the inputs of NLV3."""
