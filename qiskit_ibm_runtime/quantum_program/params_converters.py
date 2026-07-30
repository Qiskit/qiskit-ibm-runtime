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

"""Converters for quantum program params."""

from __future__ import annotations

from typing import TYPE_CHECKING, NamedTuple

from ibm_quantum_schemas.executor.version_0_1 import ParamsModel as ParamsModel_0_1
from ibm_quantum_schemas.executor.version_0_2 import ParamsModel as ParamsModel_0_2
from ibm_quantum_schemas.executor.version_1_0 import ParamsModel as ParamsModel_1_0
from ibm_quantum_schemas.executor.version_1_1 import ParamsModel as ParamsModel_1_1
from ibm_quantum_schemas.executor.version_2_0 import ParamsModel as ParamsModel_2_0

from .converters import (
    quantum_program_from_0_1,
    quantum_program_from_0_2,
    quantum_program_from_1_0,
    quantum_program_from_1_1,
    quantum_program_from_2_0,
    quantum_program_to_0_1,
    quantum_program_to_0_2,
    quantum_program_to_1_0,
    quantum_program_to_1_1,
    quantum_program_to_2_0,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from ibm_quantum_schemas.common import BaseParamsModel

    from ..options_models import ExecutorOptions
    from .quantum_program import QuantumProgram


class ParamsConverter(NamedTuple):
    """A helper to store params models and converters."""

    model: type[BaseParamsModel]
    """The model describing the executor inputs, or 'params'."""

    decoder: Callable[[BaseParamsModel], tuple[QuantumProgram, ExecutorOptions]]
    """A function to decode the inputs of executor."""

    encoder: Callable[[QuantumProgram, ExecutorOptions], BaseParamsModel]
    """A function to encode the inputs of executor."""


QUANTUM_PROGRAM_PARAMS_CONVERTERS = {
    "v0.1": ParamsConverter(ParamsModel_0_1, quantum_program_from_0_1, quantum_program_to_0_1),
    "v0.2": ParamsConverter(ParamsModel_0_2, quantum_program_from_0_2, quantum_program_to_0_2),
    "v1.0": ParamsConverter(ParamsModel_1_0, quantum_program_from_1_0, quantum_program_to_1_0),
    "v1.1": ParamsConverter(ParamsModel_1_1, quantum_program_from_1_1, quantum_program_to_1_1),
    "v2.0": ParamsConverter(ParamsModel_2_0, quantum_program_from_2_0, quantum_program_to_2_0),
}
"""Converter to/from schema model for the inputs of executor."""
