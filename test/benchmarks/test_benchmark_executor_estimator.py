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

"""Benchmarks for executor_estimator."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from qiskit_ibm_runtime.quantum_program.quantum_program import QuantumProgram

import numpy as np
import pytest
from qiskit.quantum_info import SparsePauliOp
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

from qiskit_ibm_runtime.decoders.quantum_program.decoder import QuantumProgramResultDecoder
from qiskit_ibm_runtime.executor_estimator.prepare import prepare
from qiskit_ibm_runtime.fake_provider import FakeBrisbane
from qiskit_ibm_runtime.options_models.estimator import EstimatorOptions
from qiskit_ibm_runtime.results.quantum_program import (
    QuantumProgramItemResult,
    QuantumProgramResult,
)

from ..utils import make_mirror_circuit_with_phases


@pytest.mark.benchmark
def test_executor_estimator_prepare(benchmark):
    """Benchmark the prepare() method from executor_estimator/prepare.py."""
    backend = FakeBrisbane()
    if benchmark.disabled:
        num_qubits = 5
        num_layers = 10
        num_shots = 100
    else:
        num_qubits = 100
        num_layers = 20
        num_shots = 100000

    coerced_pubs = create_test_pubs(backend, num_qubits=num_qubits, num_layers=num_layers)

    options = EstimatorOptions()
    options.resilience_level = 0

    def run_prepare():
        prepare(
            coerced_pubs,
            options,
            precision=1 / np.sqrt(num_shots),
            add_tags=False,
            backend=backend,
        )

    benchmark(run_prepare)


@pytest.mark.benchmark
def test_executor_estimator_post_processor(benchmark):
    """Benchmark the estimator post-processor via QuantumProgramResultDecoder."""
    backend = FakeBrisbane()

    if benchmark.disabled:
        num_qubits = 5
        num_layers = 10
        num_shots = 100
    else:
        num_qubits = 100
        num_layers = 20
        num_shots = 100000

    pubs = create_test_pubs(backend, num_qubits=num_qubits, num_layers=num_layers)

    options = EstimatorOptions()
    options.resilience_level = 0

    # First, run prepare once to get the baseline quantum program structure
    quantum_program, _ = prepare(
        pubs,
        options,
        precision=1 / np.sqrt(num_shots),
        add_tags=False,
        backend=backend,
    )

    # Generate dummy results
    quantum_program_result = create_dummy_result(quantum_program)

    def run_post_processor():
        QuantumProgramResultDecoder._apply_post_processing(quantum_program_result)

    benchmark(run_post_processor)


def create_test_pubs(backend, num_qubits, num_layers):
    """Helper to set up pubs based on mirror circuit."""
    pm = generate_preset_pass_manager(optimization_level=1, target=backend.target)

    circuit = make_mirror_circuit_with_phases(
        backend,
        num_qubits=num_qubits,
        layers=num_layers,
        add_measurement=False,
        add_rx=True,
    )
    isa_circuit = pm.run(circuit)

    observables = [
        SparsePauliOp("Z" * num_qubits).apply_layout(isa_circuit.layout),
        SparsePauliOp("X" * num_qubits).apply_layout(isa_circuit.layout),
    ]

    parameter_values = np.array(
        [
            [0.1] * num_qubits,
            [0.2] * num_qubits,
        ]
    )

    return [(isa_circuit, observables, parameter_values)]


def create_dummy_result(quantum_program: QuantumProgram) -> QuantumProgramResult:
    """Simulate execution by creating a QuantumProgramResult matching the program structure."""
    result_data = []
    passthrough = cast("dict[str, Any]", quantum_program.passthrough_data)
    post_processor_data = passthrough["post_processor"]
    param_basis_pairs_lists = post_processor_data["param_basis_pairs"]

    for i, item in enumerate(quantum_program.items):
        num_configs = len(param_basis_pairs_lists[i])
        num_randomizations = 1
        num_shots = quantum_program.shots
        num_bits = item.circuit.num_qubits

        meas_shape = (num_randomizations, num_configs, num_shots, num_bits)
        meas_data = np.random.randint(0, 2, size=meas_shape).astype(bool)

        result_data.append(QuantumProgramItemResult({"_meas": meas_data}))

    quantum_program_result = QuantumProgramResult(
        data=result_data,
        metadata=None,
        passthrough_data=quantum_program.passthrough_data,
    )
    quantum_program_result._semantic_role = "estimator_v2"
    return quantum_program_result
