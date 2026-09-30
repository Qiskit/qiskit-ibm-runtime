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

"""Standalone assertion helpers for client-side sampler tests."""

from __future__ import annotations

from copy import deepcopy
from typing import TYPE_CHECKING

from qiskit.circuit import BoxOp
from samplomatic import ChangeBasis, InjectNoise, Tag
from samplomatic.utils import get_annotation

if TYPE_CHECKING:
    from qiskit.circuit import QuantumCircuit


def assert_circuits_equal_ignoring_annotations(
    circuit_1: QuantumCircuit, circuit_2: QuantumCircuit
) -> None:
    """Assert two circuits are equal, ignoring any annotations on box operations."""

    def strip_annotations(circuit: QuantumCircuit) -> QuantumCircuit:
        """Return a copy of the circuit without annotations.

        Annotations cannot be mutated in python space, so data is recreated.
        """
        new_data = []
        for instr in circuit.data:
            if isinstance(instr.operation, BoxOp):
                stripped_op = deepcopy(instr.operation)
                stripped_op.annotations = []
                new_data.append(instr.replace(operation=stripped_op))
            else:
                new_data.append(instr)
        circuit_copy = circuit.copy_empty_like()
        circuit_copy.data = new_data
        return circuit_copy

    assert strip_annotations(circuit_1) == strip_annotations(circuit_2)


def assert_circuits_annotations_are_equal(
    circuit_1: QuantumCircuit, circuit_2: QuantumCircuit
) -> None:
    """Assert annotations on box operations are equal between two circuits, up to ref."""
    assert len(circuit_1.data) == len(circuit_2.data)

    for instr1, instr2 in zip(circuit_1.data, circuit_2.data):
        if not isinstance(instr1.operation, BoxOp):
            continue
        assert isinstance(instr2.operation, BoxOp)

        annotations_1 = instr1.operation.annotations
        annotations_2 = instr2.operation.annotations
        assert len(annotations_1) == len(annotations_2)

        for ann1 in annotations_1:
            # Look up the matching annotation in circuit_2 by type (order-independent).
            ann2 = get_annotation(instr2.operation, type(ann1))
            assert ann2 is not None, (
                f"circuit_2 box is missing a {type(ann1).__name__} annotation"
            )
            if isinstance(ann1, (ChangeBasis, InjectNoise)):
                # ref is a runtime-unique identifier; normalise ann2's ref to ann1's before
                # comparing so only the semantically meaningful fields are checked.
                ann2_normalised = deepcopy(ann2)
                ann2_normalised.ref = ann1.ref
                assert ann1 == ann2_normalised
            elif isinstance(ann1, Tag):
                # Tag has only ref. Nothing to compare beyond presence.
                continue
            else:
                # Twirl has no ref; also future-proofs for new annotation types.
                assert ann1 == ann2
