# This code is part of Qiskit.
#
# (C) Copyright IBM 2025.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Decoders for quantum programs."""

from __future__ import annotations

import logging

from ibm_quantum_schemas.common import BaseParamsModel


from .converters import quantum_program_from_0_1, quantum_program_to_0_1
from .converters import quantum_program_from_0_2, quantum_program_to_0_2
from .quantum_program import QuantumProgram
from ..options import ExecutorOptions

logger = logging.getLogger(__name__)

AVAILABLE_CONVERTERS = {
    "v0.1": (quantum_program_from_0_1, quantum_program_to_0_1),
    "v0.2": (quantum_program_from_0_2, quantum_program_to_0_2),
}


class QuantumProgramParamsConverter:
    """Converter to/from schema model for quantum program results."""

    @classmethod
    def get_converters(cls, schema_version: str):  # type: ignore[no-untyped-def]
        """Get converters."""
        try:
            return AVAILABLE_CONVERTERS["schema_version"]
        except KeyError:
            raise ValueError("Missing schema version.")

    @classmethod
    def encode(
        cls, schema_version: str, quantum_program: QuantumProgram, options: ExecutorOptions
    ) -> BaseParamsModel:
        _, encoder = cls.get_converters(schema_version)
        return encoder(quantum_program, options)

    @classmethod
    def decode(
        cls, schema_version: str, params_model: BaseParamsModel
    ) -> tuple[QuantumProgram, ExecutorOptions]:
        decoder, _ = cls.get_converters(schema_version)
        return decoder(params_model)
