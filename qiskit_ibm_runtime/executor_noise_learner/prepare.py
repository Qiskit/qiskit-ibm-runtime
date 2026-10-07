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

from qiskit.transpiler import PassManager
from qiskit_addon_utils.noise_management.constants import DEFAULT_SPECTATOR_CREG_NAME
from qiskit_addon_utils.noise_management.post_selection.transpiler.passes import (
    AddPostSelectionMeasures,
    AddSpectatorMeasures,
)
from qiskit_mitigation.postselection.passes import (
    AddPostCircuitNonMarkovianErrorChecks,
    AddPreCircuitNonMarkovianErrorChecks,
    AddSpectatorPostCircuitNonMarkovianErrorChecks,
    AddSpectatorPreCircuitNonMarkovianErrorChecks,
)
from qiskit_noise_learning.protocols import prepare_learning_program

from ..options_models.converters import noise_learner_options_to_executor_options

if TYPE_CHECKING:
    from collections.abc import Iterable

    from qiskit.circuit import CircuitInstruction
    from qiskit.providers import BackendV2

    from ..options_models.executor import ExecutorOptions
    from ..options_models.noise_learner_v3 import NoiseLearnerV3Options
    from ..quantum_program import QuantumProgram


def prepare(
    instructions: Iterable[CircuitInstruction],
    options: NoiseLearnerV3Options,
    backend: BackendV2,
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
    post_selection = options.post_selection
    pre = options.bit_flip_checks.pre_circuit
    post = options.bit_flip_checks.post_circuit
    coupling_map = backend.target.build_coupling_map()
    pass_manager = None

    if post_selection.enable:
        post_selection_passes = [
            AddSpectatorMeasures(coupling_map, spectator_creg_name=DEFAULT_SPECTATOR_CREG_NAME),
            AddPostSelectionMeasures(post_selection.x_pulse_type),
        ]
        pass_manager = PassManager(post_selection_passes)
    elif pre.enable or post.enable:
        pre_x_pulse_type = pre.x_pulse_type if pre.enable else None
        post_x_pulse_type = post.x_pulse_type if post.enable else None
        bit_flip_passes = []
        if pre_x_pulse_type is not None:
            bit_flip_passes.append(AddPreCircuitNonMarkovianErrorChecks(pre_x_pulse_type))
            bit_flip_passes.append(
                AddSpectatorPreCircuitNonMarkovianErrorChecks(coupling_map, pre_x_pulse_type)
            )
        if post_x_pulse_type is not None:
            bit_flip_passes.append(AddPostCircuitNonMarkovianErrorChecks(post_x_pulse_type))
            bit_flip_passes.append(
                AddSpectatorPostCircuitNonMarkovianErrorChecks(coupling_map, post_x_pulse_type)
            )
            pass_manager = PassManager(bit_flip_passes)
    quantum_program = prepare_learning_program(
        backend=backend,
        instructions=instructions,
        num_randomizations=options.num_randomizations,
        shots_per_randomization=options.shots_per_randomization,
        fragment_depths=options.layer_pair_depths,
        creg_prefix="meas",
        local_clifford_ref_prefix="c",
        pass_manager=pass_manager,
    )
    quantum_program.passthrough_data["post_processor"] = {  # type: ignore[index]
        "version": "v0.1",
        "options": options.model_dump(),
    }
    return quantum_program, executor_options
