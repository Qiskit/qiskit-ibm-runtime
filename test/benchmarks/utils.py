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

"""Shared utilities for executor benchmark tests."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
from samplomatic.quantum_program import CircuitItem, SamplexItem

from qiskit_ibm_runtime.fake_provider.executor.broadcast_sample import broadcast_sample
from qiskit_ibm_runtime.results.quantum_program import (
    QuantumProgramItemResult,
    QuantumProgramResult,
)

if TYPE_CHECKING:
    from qiskit_ibm_runtime.quantum_program.quantum_program import QuantumProgram


def create_dummy_executor_result(quantum_program: QuantumProgram) -> QuantumProgramResult:
    """Simulate what the executor produces for a quantum program.

    Correct shapes and result structure will be returned, but data will be random boolean values.

    Args:
        quantum_program: The prepared quantum program whose structure is used
            to generate dummy result data.

    Returns:
        A :class:`~.QuantumProgramResult` with random data matching the program structure.
    """
    rng = np.random.default_rng(0)
    result_data = []

    for item in quantum_program.items:
        shots = quantum_program.shots

        if isinstance(item, SamplexItem):
            # Get all samplex outputs (flips, pauli_signs, …) with correct shapes
            samplex_data = broadcast_sample(item.samplex, item.samplex_arguments, item.shape, rng)
            samplex_data.pop("parameter_values", None)

            # Replace circuit measurement registers with random data
            for creg in item.circuit.cregs:
                shape = item.shape + (shots, creg.size)
                samplex_data[creg.name] = np.random.randint(0, 2, size=shape).astype(bool)
        elif isinstance(item, CircuitItem):
            # No-twirling path: shape is the parameter sweep shape
            param_sweep_shape = (
                item.circuit_arguments.shape[:-1] if item.circuit_arguments is not None else ()
            )
            samplex_data = {}
            for creg in item.circuit.cregs:
                data_shape = param_sweep_shape + (shots, creg.size)
                samplex_data[creg.name] = np.random.randint(0, 2, size=data_shape).astype(bool)
        else:
            raise ValueError(f"Unsupported item type: {type(item)}")

        result_data.append(QuantumProgramItemResult(samplex_data))

    quantum_program_result = QuantumProgramResult(
        data=result_data,
        passthrough_data=quantum_program.passthrough_data,
    )
    quantum_program_result._semantic_role = quantum_program._semantic_role
    return quantum_program_result
