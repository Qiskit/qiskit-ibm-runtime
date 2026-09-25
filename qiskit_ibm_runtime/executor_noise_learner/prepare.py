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

"""Prepare function for client-side noise learner primitive."""

from __future__ import annotations

from typing import TYPE_CHECKING

from qiskit import QuantumCircuit

from ..options_models.converters import noise_learner_options_to_executor_options
from ..quantum_program import QuantumProgram

if TYPE_CHECKING:
    from collections.abc import Iterable

    from qiskit.circuit import CircuitInstruction
    from qiskit.providers import BackendV2

    from ..options_models.executor import ExecutorOptions
    from ..options_models.noise_learner_v3 import NoiseLearnerV3Options


# TODO: use `qiskit_noise_learning.prepare` once available
def prepare(
    instructions: Iterable[CircuitInstruction],
    options: NoiseLearnerV3Options,
    backend: BackendV2 | None = None,
) -> tuple[QuantumProgram, ExecutorOptions]:
    """Convert a sequence of instructions to a quantum program and map options.

    Args:
        instructions: Iterable of circuit instructions.
        options: The noise learner options.
        backend: The backend for which the program is prepared.

    Returns:
        A tuple containing:

        - :class:`~.QuantumProgram` with :class:`~.CircuitItem` or :class:`~.SamplexItem`
            objects for each instruction, with passthrough_data configured for post-processing.
        - :class:`~.ExecutorOptions` The finalized executor options.
    """
    executor_options = noise_learner_options_to_executor_options(options)
    quantum_program = QuantumProgram(shots=1)

    circuit = QuantumCircuit(1)
    circuit.measure_all()
    quantum_program.append_circuit_item(circuit)
    return quantum_program, executor_options
