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

"""Custom TestCase for client-side sampler tests."""

from __future__ import annotations

from typing import TYPE_CHECKING

from test.ibm_test_case import IBMTestCase

from .asserts import (
    assert_circuits_annotations_are_equal,
    assert_circuits_equal_ignoring_annotations,
)

if TYPE_CHECKING:
    from qiskit.circuit import QuantumCircuit


class IBMBoxedCircuitTestCase(IBMTestCase):
    """TestCase with assertions for boxed circuits."""

    def assertCircuitsEqualIgnoringAnnotations(
        self, circuit_1: QuantumCircuit, circuit_2: QuantumCircuit
    ) -> None:
        """Assert two circuits are equal, ignoring any annotations on box operations."""
        assert_circuits_equal_ignoring_annotations(circuit_1, circuit_2)

    def assertCircuitsAnnotationsAreEqual(
        self, circuit_1: QuantumCircuit, circuit_2: QuantumCircuit
    ) -> None:
        """Assert annotations on box operations are equal between two circuits, up to ref."""
        assert_circuits_annotations_are_equal(circuit_1, circuit_2)
