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

"""Utils for Sampler unit tests."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit import Parameter
from qiskit.primitives.containers.sampler_pub import SamplerPub
from samplomatic import Tag
from samplomatic.utils import get_annotation

if TYPE_CHECKING:
    from collections.abc import Sequence

    from qiskit.circuit import CircuitInstruction

    from qiskit_ibm_runtime.quantum_program import QuantumProgram


def extract_barrier_tags(circuit: QuantumCircuit) -> set[str]:
    """Extract all @tag=<tag> identifiers from barrier labels in a circuit."""
    tags = set()
    for instruction in circuit.data:
        if instruction.operation.name == "barrier" and instruction.operation.label:
            for part in instruction.operation.label.split():
                if "@tag=" in part:
                    tags.add(part.split("@tag=")[1])
    return tags


def extract_program_barrier_tags(program: QuantumProgram) -> set[str]:
    """Extract all barrier tags from all circuit items in a QuantumProgram."""
    tags = set()
    for item in program.items:
        tags.update(extract_barrier_tags(item.circuit))
    return tags


def extract_layer_tags(layers: Sequence[CircuitInstruction]) -> set[str]:
    """Extract Tag.ref from a sequence of boxed layers."""
    tags = set()
    for layer in layers:
        tag_annotation = get_annotation(layer.operation, Tag)
        if tag_annotation is not None:
            tags.add(tag_annotation.ref)
    return tags


@dataclass(frozen=True)
class SamplerCircuitScenario:
    """A circuit scenario for testing Sampler prepare and layer correspondence."""

    label: str
    pub: SamplerPub
    has_parameters: bool
    num_gate_layers: int


def _make_sampler_circuit_scenarios() -> list[SamplerCircuitScenario]:
    # non-parametric: 2 qubits, H + CX + measurement
    circuit_non_parametric = QuantumCircuit(2, 2)
    circuit_non_parametric.h(0)
    circuit_non_parametric.cx(0, 1)
    circuit_non_parametric.measure(range(2), range(2))

    # parametric: 2 qubits, Rx(theta) + CX + measurement
    circuit_parametric = QuantumCircuit(2, 2)
    circuit_parametric.rx(Parameter("theta"), 0)
    circuit_parametric.cx(0, 1)
    circuit_parametric.measure(range(2), range(2))

    # mid-circuit: 2 qubits, H + CX + mid-circuit measurement + H + final measurement
    circuit_mid_circuit = QuantumCircuit(2, 3)
    circuit_mid_circuit.h(0)
    circuit_mid_circuit.cx(0, 1)
    circuit_mid_circuit.measure(0, 0)
    circuit_mid_circuit.h(0)
    circuit_mid_circuit.measure(0, 1)
    circuit_mid_circuit.measure(1, 2)

    # multi-layer: 3 qubits, cx(0,1) repeated twice, cx(1,2) repeated twice
    # Tests layer deduplication across multiple applications of identical gate layers
    circuit_multi_layer = QuantumCircuit(3, 3)
    circuit_multi_layer.cx(0, 1)
    circuit_multi_layer.cx(0, 1)
    circuit_multi_layer.cx(1, 2)
    circuit_multi_layer.cx(1, 2)
    circuit_multi_layer.measure(range(3), range(3))

    return [
        SamplerCircuitScenario(
            label="non_parametric",
            pub=SamplerPub.coerce(circuit_non_parametric, shots=1024),
            has_parameters=False,
            num_gate_layers=1,
        ),
        SamplerCircuitScenario(
            label="parametric",
            pub=SamplerPub.coerce((circuit_parametric, np.array([[0.1], [0.2]])), shots=1024),
            has_parameters=True,
            num_gate_layers=1,
        ),
        SamplerCircuitScenario(
            label="mid_circuit",
            pub=SamplerPub.coerce(circuit_mid_circuit, shots=1024),
            has_parameters=False,
            num_gate_layers=2,
        ),
        SamplerCircuitScenario(
            label="multi_layer",
            pub=SamplerPub.coerce(circuit_multi_layer, shots=1024),
            has_parameters=False,
            num_gate_layers=2,
        ),
    ]


SAMPLER_CIRCUIT_SCENARIOS: list[SamplerCircuitScenario] = _make_sampler_circuit_scenarios()
