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

from typing import cast, Any
import numpy as np
import pytest
from qiskit_ibm_runtime.fake_provider import FakeBrisbane

from qiskit.quantum_info import SparsePauliOp
from qiskit.primitives.containers.estimator_pub import EstimatorPub
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

from qiskit_ibm_runtime.executor_estimator.prepare import prepare
from qiskit_ibm_runtime.executor_estimator.estimator import EstimatorV2
from qiskit_ibm_runtime.decoders.executor_estimator.post_processor_v0_1 import (
    estimator_v2_post_processor_v0_1,
)
from qiskit_ibm_runtime.results.quantum_program import (
    QuantumProgramItemResult,
    QuantumProgramResult,
)

from ..utils import make_mirror_circuit_with_phases


def _setup_test_pubs(benchmark, backend):
    """Helper to set up pubs for both benchmarks."""
    if benchmark.disabled:
        # Fast execution for non-benchmark runs
        num_qubits = 5
    else:
        # Realistic workload for benchmarking
        num_qubits = 100

    pm = generate_preset_pass_manager(optimization_level=1, target=backend.target)

    # Generate mirror circuit with parameterized RX gates on each qubit
    circuit = make_mirror_circuit_with_phases(
        backend,
        num_qubits=num_qubits,
        layers=400,
        add_measurement=False,
        add_rx=True,
    )
    isa_circuit = pm.run(circuit)

    # Create observables with layout applied
    observables = [
        SparsePauliOp("Z" * num_qubits).apply_layout(isa_circuit.layout),
        SparsePauliOp("X" * num_qubits).apply_layout(isa_circuit.layout),
    ]

    # Create 2 parameter sets as a numpy array
    parameter_values = np.array([
        [0.1] * num_qubits,
        [0.2] * num_qubits,
    ])

    pubs = [(isa_circuit, observables, parameter_values)]
    coerced_pubs = [EstimatorPub.coerce(pub, precision=None) for pub in pubs]  # type: ignore[arg-type]
    return coerced_pubs, num_qubits


@pytest.mark.benchmark
def test_executor_estimator_prepare(benchmark):
    """Benchmark the prepare() method from executor_estimator/prepare.py."""
    backend = FakeBrisbane()
    coerced_pubs, _ = _setup_test_pubs(benchmark, backend)
    estimator = EstimatorV2(backend)
    estimator.options.resilience_level = 0
    options = estimator.finalize_options()
    shots = 100000

    def run_prepare():
        prepare(
            coerced_pubs,
            options,
            shots=shots,
            add_tags=False,
            backend=backend,
        )

    benchmark(run_prepare)


@pytest.mark.benchmark
def test_executor_estimator_post_processor(benchmark):
    """Benchmark the estimator_v2_post_processor_v0_1() method."""
    backend = FakeBrisbane()
    coerced_pubs, _ = _setup_test_pubs(benchmark, backend)
    estimator = EstimatorV2(backend)
    estimator.options.resilience_level = 0
    options = estimator.finalize_options()
    shots = 1000

    # First, run prepare once to get the baseline quantum program structure
    quantum_program, _ = prepare(
        coerced_pubs,
        options,
        shots=shots,
        add_tags=False,
        backend=backend,
    )

    passthrough = cast(dict[str, Any], quantum_program.passthrough_data)

    # Manually attach post-processor run context fields
    passthrough["post_processor"]["options"] = options.model_dump(
        exclude={"resilience": {"noise_model"}}
    )
    passthrough["post_processor"]["shots"] = shots
    passthrough["post_processor"]["precision"] = None

    # Simulate executor's execution by creating a dummy QuantumProgramResult
    result_data = []
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

    def run_post_processor():
        return estimator_v2_post_processor_v0_1(quantum_program_result)

    benchmark(run_post_processor)
