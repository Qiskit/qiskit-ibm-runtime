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

"""Benchmarks for executor_sampler."""

from __future__ import annotations

import numpy as np
import pytest
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

from qiskit_ibm_runtime.decoders.quantum_program.decoder import QuantumProgramResultDecoder
from qiskit_ibm_runtime.executor_sampler.prepare import prepare
from qiskit_ibm_runtime.fake_provider import FakeMarrakesh
from qiskit_ibm_runtime.options_models.sampler import SamplerOptions

from ..utils import make_mirror_circuit_with_phases
from .utils import create_dummy_executor_result

PREPARE_VARIANTS = {
    "vanilla": {},
    "twirling": {
        "twirling": {"enable_gates": True, "enable_measure": True},
    },
    "twirling_dd": {
        "twirling": {"enable_gates": True, "enable_measure": True},
        "dynamical_decoupling": {"enable": True},
    },
    "dd_only": {
        "dynamical_decoupling": {"enable": True},
    },
}

POST_PROCESS_VARIANTS = {
    "vanilla": {},
    "twirling": {
        "twirling": {"enable_gates": True, "enable_measure": True},
    },
}


@pytest.mark.parametrize(
    "variant_id,variant_options",
    PREPARE_VARIANTS.items(),
)
def test_executor_sampler_prepare(benchmark, variant_id, variant_options):
    """Benchmark prepare() for different twirling and dynamical decoupling configurations."""
    if benchmark.disabled:
        num_qubits = 3
        num_layers = 10
        num_shots = 100
    else:
        num_qubits = 100
        num_layers = 20
        num_shots = 200000

    backend = FakeMarrakesh()

    coerced_pubs = create_test_pubs(backend, num_qubits=num_qubits, num_layers=num_layers)

    options = SamplerOptions()
    options.update(**variant_options)

    def run_prepare():
        prepare(
            coerced_pubs,
            options,
            shots=num_shots,
            add_tags=False,
            backend=backend,
        )

    benchmark(run_prepare)


@pytest.mark.parametrize(
    "variant_id,variant_options",
    POST_PROCESS_VARIANTS.items(),
)
def test_executor_sampler_post_processor(benchmark, variant_id, variant_options):
    """Benchmark the sampler post-processor for different twirling/DD configurations."""
    if benchmark.disabled:
        num_qubits = 3
        num_shots = 100
    else:
        num_qubits = 100
        num_shots = 200000

    backend = FakeMarrakesh()

    pubs = create_test_pubs(backend, num_qubits=num_qubits, num_layers=100)

    options = SamplerOptions()
    options.update(**variant_options)

    # Run prepare once to get the quantum program structure for this variant
    quantum_program, _ = prepare(
        pubs,
        options,
        shots=num_shots,
        add_tags=False,
        backend=backend,
    )
    quantum_program._semantic_role = "sampler_v2"

    # _apply_post_processing mutates the executor result, so we need to re-generate it
    # for each benchmarking round:
    def setup():
        # return args, kwargs to test function
        return (create_dummy_executor_result(quantum_program),), {}

    benchmark.pedantic(
        QuantumProgramResultDecoder._apply_post_processing,
        setup=setup,
        rounds=10,
    )


def create_test_pubs(backend, num_qubits, num_layers):
    """Helper to set up pubs based on mirror circuit with measurement."""
    pm = generate_preset_pass_manager(optimization_level=1, target=backend.target)

    circuit = make_mirror_circuit_with_phases(
        backend,
        num_qubits=num_qubits,
        layers=num_layers,
    )
    isa_circuit = pm.run(circuit)

    parameter_values = np.array(
        [
            [0.1] * num_qubits,
            [0.2] * num_qubits,
        ]
    )

    return [(isa_circuit, parameter_values)]
