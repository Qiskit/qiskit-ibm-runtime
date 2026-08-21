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

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from qiskit_ibm_runtime.quantum_program.quantum_program import QuantumProgram

import numpy as np
import pytest
from qiskit.quantum_info import PauliLindbladMap, SparsePauliOp
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from samplomatic import InjectNoise
from samplomatic.utils import get_annotation

from qiskit_ibm_runtime.decoders.quantum_program.decoder import QuantumProgramResultDecoder
from qiskit_ibm_runtime.executor_estimator.finalize_options import finalize_estimator_options
from qiskit_ibm_runtime.executor_estimator.prepare import prepare
from qiskit_ibm_runtime.executor_estimator.utils import find_unique_layers
from qiskit_ibm_runtime.executor_local_mode.broadcast_sample import broadcast_sample
from qiskit_ibm_runtime.fake_provider import FakeBrisbane
from qiskit_ibm_runtime.options_models.estimator import EstimatorOptions
from qiskit_ibm_runtime.quantum_program import SamplexItem
from qiskit_ibm_runtime.results.quantum_program import (
    QuantumProgramItemResult,
    QuantumProgramResult,
)

from ..utils import make_mirror_circuit_with_phases

# ---------------------------------------------------------------------------
# Option configurations – one per dispatch branch in prepare._build_quantum_program
# ---------------------------------------------------------------------------

# Branch: prepare_vanilla (default – no ZNE, no PEC)
VANILLA = {
    "id": "vanilla",
    "resilience_level": 0,
}

# Branch: prepare_vanilla with measure-error learning (TREX / measure_mitigation)
VANILLA_TREX = {
    "id": "vanilla_trex",
    "resilience_level": 0,
    "twirling": {"enable_gates": True, "enable_measure": True},
    "resilience": {"measure_mitigation": True},
}

# Branch: prepare_zne  (ZNE with gate_folding amplifier)
ZNE_GATE_FOLDING = {
    "id": "zne_gate_folding",
    "resilience_level": 0,
    "twirling": {"enable_gates": True, "enable_measure": True},
    "resilience": {
        "zne_mitigation": True,
        "zne": {"amplifier": "gate_folding"},
    },
}

# Branch: prepare_pea  (ZNE with PEA amplifier)
ZNE_PEA = {
    "id": "zne_pea",
    "resilience_level": 0,
    "twirling": {"enable_gates": True, "enable_measure": True},
    "resilience": {
        "zne_mitigation": True,
        "zne": {"amplifier": "pea"},
    },
}

# Branch: prepare_pec
PEC = {
    "id": "pec",
    "resilience_level": 0,
    "twirling": {"enable_gates": True, "enable_measure": True},
    "resilience": {
        "pec_mitigation": True,
    },
}

_PREPARE_VARIANTS = [VANILLA, VANILLA_TREX, ZNE_GATE_FOLDING, ZNE_PEA, PEC]

# Variants that require a noise model (PEC and PEA use inject_noise=True in prepare)
_NEEDS_NOISE_MODEL = {"pec", "zne_pea"}


@pytest.mark.benchmark
@pytest.mark.parametrize(
    "variant",
    _PREPARE_VARIANTS,
    ids=[v["id"] for v in _PREPARE_VARIANTS],
)
def test_executor_estimator_prepare(benchmark, variant):
    """Benchmark prepare() for each prepare-function dispatch branch.

    Covered branches (see executor_estimator/prepare._build_quantum_program):
      - ``vanilla``          → :func:`prepare_vanilla`
      - ``vanilla_trex``     → :func:`prepare_vanilla` with measure-noise learning
      - ``zne_gate_folding`` → :func:`prepare_zne`
      - ``zne_pea``          → :func:`prepare_pea`
      - ``pec``              → :func:`prepare_pec`
    """
    if benchmark.disabled:
        num_qubits = 3
        num_layers = 10
        num_shots = 100
    else:
        num_qubits = 100
        num_layers = 20
        num_shots = 200000

    backend = FakeBrisbane()
    coerced_pubs = create_test_pubs(backend, num_qubits=num_qubits, num_layers=num_layers)
    options = EstimatorOptions()
    options.update(**{k: v for k, v in variant.items() if k != "id"})
    if variant["id"] in _NEEDS_NOISE_MODEL:
        options.resilience.noise_model = create_identity_noise_model(coerced_pubs, options)

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
@pytest.mark.parametrize(
    "variant",
    _PREPARE_VARIANTS,
    ids=[v["id"] for v in _PREPARE_VARIANTS],
)
def test_executor_estimator_post_processor(benchmark, variant):
    """Benchmark the estimator post-processor for each prepare-function dispatch branch.

    Each branch produces a different ``passthrough_data`` structure, exercising
    distinct post-processing code paths in
    :meth:`~.QuantumProgramResultDecoder._apply_post_processing`.

    Covered branches (see executor_estimator/prepare._build_quantum_program):
      - ``vanilla``          → :func:`prepare_vanilla`
      - ``vanilla_trex``     → :func:`prepare_vanilla` with measure-noise learning
      - ``zne_gate_folding`` → :func:`prepare_zne`
      - ``zne_pea``          → :func:`prepare_pea`
      - ``pec``              → :func:`prepare_pec`
    """
    if benchmark.disabled:
        # Qubit count smaller than 6 on Brisbane causes error:
        # Results must contain ``'pauli_signs'`` in the data if PEC is used.
        # Weirdly using AER as a backend can accept <6 qubits.
        num_qubits = 6
        num_layers = 10
        num_shots = 100
    else:
        num_qubits = 100
        num_layers = 20
        num_shots = 200000

    backend = FakeBrisbane()
    pubs = create_test_pubs(backend, num_qubits=num_qubits, num_layers=num_layers)
    options = EstimatorOptions()
    options.update(**{k: v for k, v in variant.items() if k != "id"})
    if variant["id"] in _NEEDS_NOISE_MODEL:
        options.resilience.noise_model = create_identity_noise_model(pubs, options)

    # Run prepare once to get the quantum program structure for this variant
    quantum_program, _ = prepare(
        pubs,
        options,
        precision=1 / np.sqrt(num_shots),
        add_tags=False,
        backend=backend,
    )

    # Generate dummy results matching the prepared program structure
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


def create_identity_noise_model(pubs, options: EstimatorOptions) -> dict:
    """Build a trivial identity noise model for PEC/PEA variants."""
    from qiskit.primitives.containers.estimator_pub import EstimatorPub

    coerced_pubs = [EstimatorPub.coerce(pub) for pub in pubs]
    finalized_options = finalize_estimator_options(options)
    layers = find_unique_layers(
        coerced_pubs,
        twirling_options=finalized_options.twirling,
        measure_noise_learning=finalized_options.resilience.measure_noise_learning
        if finalized_options.resilience.measure_mitigation
        else None,
        inject_noise=True,
    )
    noise_model = {}
    for layer in layers:
        annot = get_annotation(layer.operation, InjectNoise)
        if annot is not None:
            noise_model[annot.ref] = PauliLindbladMap.identity(layer.operation.num_qubits)
    return noise_model


def create_dummy_result(quantum_program: QuantumProgram) -> QuantumProgramResult:
    """Simulate what the executor produces for a quantum program.

    Mirrors :func:`~.run_quantum_program` exactly: runs ``broadcast_sample`` to
    get all samplex outputs (flips, pauli_signs, etc.), pops ``parameter_values``,
    then adds random bit-arrays for each classical register in place of real
    AerSampler results.
    """
    rng = np.random.default_rng(0)
    result_data = []

    for item in quantum_program.items:
        assert isinstance(item, SamplexItem)
        shots = quantum_program.shots

        # Get all samplex outputs (flips, pauli_signs, …) with correct shapes
        samplex_data = broadcast_sample(item.samplex, item.samplex_arguments, item.shape, rng)
        samplex_data.pop("parameter_values", None)

        # Replace circuit measurement registers with random data
        for creg in item.circuit.cregs:
            shape = item.shape + (shots, creg.size)
            samplex_data[creg.name] = np.random.randint(0, 2, size=shape).astype(bool)

        result_data.append(QuantumProgramItemResult(samplex_data))

    quantum_program_result = QuantumProgramResult(
        data=result_data,
        metadata=None,
        passthrough_data=quantum_program.passthrough_data,
    )
    quantum_program_result._semantic_role = "estimator_v2"
    return quantum_program_result
