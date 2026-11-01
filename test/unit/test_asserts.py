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

"""Tests for standalone assertion helpers in ``test/asserts.py``."""

from __future__ import annotations

import numpy as np
import pytest
from qiskit.quantum_info import PauliLindbladMap
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit_aer import AerSimulator
from samplomatic import build
from samplomatic.transpiler import generate_boxing_pass_manager
from samplomatic.utils import find_unique_box_instructions

from qiskit_ibm_runtime import Executor, QuantumProgram
from test.asserts import fail_on_missing_noise_warning
from test.utils import make_mirror_circuit_with_phases


def _make_executor_with_noise(*, omit_last_layer: bool) -> tuple[Executor, QuantumProgram]:
    """Return an ``Executor`` and program whose noise model either covers all layers or omits one.

    Args:
        omit_last_layer: When ``True``, the noise model excludes the last unique boxed layer,
            causing ``InsertNoisePass`` to emit a missing-noise warning during simulation.
    """
    backend = AerSimulator()
    circuit = make_mirror_circuit_with_phases(backend)

    pass_manager = generate_preset_pass_manager(backend=backend, optimization_level=0)
    pass_manager.post_scheduling = generate_boxing_pass_manager(
        enable_gates=True,
        enable_measures=True,
        add_tags="unique_box",
        inject_noise_site="after",
    )
    boxed_isa_circuit = pass_manager.run(circuit)

    isa_template, samplex = build(boxed_isa_circuit)
    parameter_values = np.zeros(circuit.num_parameters)

    program = QuantumProgram(shots=100)
    program.append_samplex_item(
        isa_template, samplex=samplex, samplex_arguments={"parameter_values": parameter_values}
    )

    unique_instructions = find_unique_box_instructions(
        boxed_isa_circuit,
        normalize_annotations=None,
        undress_boxes=True,
    )
    noise = PauliLindbladMap.from_list([("XI", 0.01)])

    covered = unique_instructions[:-1] if omit_last_layer else unique_instructions

    executor = Executor(mode=backend)
    executor.options.simulator.layer_noise_model = [(instr, noise) for instr in covered]

    return executor, program


class TestFailOnMissingNoiseWarning:
    """Tests for the ``fail_on_missing_noise_warning`` decorator."""

    def test_passes_when_all_layers_are_covered(self) -> None:
        """The decorator does not raise when every layer is present in the noise model."""

        @fail_on_missing_noise_warning
        def _test():
            executor, program = _make_executor_with_noise(omit_last_layer=False)
            executor.run(program).result()

        _test()  # must not raise

    def test_fails_when_a_layer_is_missing_from_the_noise_model(self) -> None:
        """The decorator raises ``AssertionError`` when a missing-tag warning is emitted."""

        @fail_on_missing_noise_warning
        def _test():
            executor, program = _make_executor_with_noise(omit_last_layer=True)
            executor.run(program).result()

        with pytest.raises(AssertionError, match="missing-noise warning"):
            _test()
