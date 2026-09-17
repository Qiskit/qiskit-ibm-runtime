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

"""Tests for SimulatorOptions."""

from __future__ import annotations

from itertools import product
from typing import TYPE_CHECKING

from ddt import data, ddt, unpack
from pydantic import ValidationError
from qiskit.circuit import QuantumCircuit
from qiskit.quantum_info import PauliLindbladMap

from qiskit_ibm_runtime.options_models.simulator import (
    BODY_POSITIONS,
    NOISE_POSITIONS,
    SimulatorOptions,
)

from ...ibm_test_case import IBMTestCase

if TYPE_CHECKING:
    from collections.abc import Callable

    from qiskit.circuit import CircuitInstruction


def _box(fill: Callable[[QuantumCircuit], object]) -> CircuitInstruction:
    """A two-qubit box instruction whose body is whatever ``fill`` puts in it."""
    circuit = QuantumCircuit(2, 2)
    with circuit.box():
        circuit.noop(range(2))
        fill(circuit)
    return circuit.data[0]


_UNBOXED = QuantumCircuit(2)
_UNBOXED.x(0)

NOISE = PauliLindbladMap.identity(2)
NOT_BOX = _UNBOXED.data[0]
BOX = _box(lambda circuit: circuit.cx(0, 1))
EMPTY_BODY_BOX = _box(lambda circuit: None)
ONE_QUBIT_BODY_BOX = _box(lambda circuit: circuit.x(0))
MEASURE_BODY_BOX = _box(lambda circuit: circuit.measure([0, 1], [0, 1]))


@ddt
class TestSimulatorOptions(IBMTestCase):
    """Tests for SimulatorOptions."""

    def test_simulator_options_default(self):
        """Test that simulator options have correct defaults."""
        options = SimulatorOptions()

        self.assertEqual(options.angle_decimals, 5)
        self.assertIsNone(options.layer_noise_model)
        self.assertIsNone(options.seed_simulator)
        self.assertTrue(options.warn_absent)

    @data(
        [(BOX, NOISE)],
        *([(BOX, NOISE, position)] for position in NOISE_POSITIONS),
        [(BOX, NOISE), (BOX, NOISE, "M")],
        # A `measure` is single-qubit but is not absorbed into the dressing, so its layer keeps a
        # body and a body-relative position stays meaningful for it.
        [(MEASURE_BODY_BOX, NOISE, "before")],
    )
    def test_entries_are_stored_exactly_as_given(self, entries):
        """Valid entries round-trip unchanged, at either arity and mixed within one list."""
        self.assertEqual(SimulatorOptions(layer_noise_model=entries).layer_noise_model, entries)

    @data("Q", "r", "Before", "", "RR")
    def test_invalid_noise_position_is_rejected(self, position):
        """An unusable position is reported with the value and the allowed set."""
        with self.assertRaisesRegex(ValidationError, "expected one of"):
            SimulatorOptions(layer_noise_model=[(BOX, NOISE, position)])

    @data(2, 3)
    def test_entry_validation_applies_at_both_arities(self, arity):
        """Carrying a position does not bypass the checks that apply to a plain entry."""
        position = () if arity == 2 else ("R",)

        with self.assertRaisesRegex(ValidationError, "does not contain a box"):
            SimulatorOptions(layer_noise_model=[(NOT_BOX, NOISE, *position)])

        with self.assertRaisesRegex(ValidationError, "Found instruction with 2"):
            SimulatorOptions(layer_noise_model=[(BOX, PauliLindbladMap.identity(1), *position)])

    def test_positions_survive_a_model_dump_round_trip(self):
        """``model_dump()`` then re-validation preserves positions, as the converters rely on."""
        options = SimulatorOptions(layer_noise_model=[(BOX, NOISE), (BOX, NOISE, "L")])

        self.assertEqual(
            SimulatorOptions(**options.model_dump()).layer_noise_model,
            options.layer_noise_model,
        )

    @data(*product(BODY_POSITIONS, (EMPTY_BODY_BOX, ONE_QUBIT_BODY_BOX)))
    @unpack
    def test_body_relative_position_needs_a_body(self, position, box):
        """Rejected where a body-relative name cannot mean two different things.

        Single-qubit gates are absorbed into the layer's dressing, so a body holding only those is
        equivalent to an empty one and both sides of it name the same point.
        """
        with self.assertRaisesRegex(ValidationError, "is ambiguous for a layer"):
            SimulatorOptions(layer_noise_model=[(box, NOISE, position)])

    @data(
        # A key must name exactly the qubits its map is defined on ...
        ({(0,): NOISE}, "but a noise model with 2"),
        # ... wherever in the mapping the offending entry sits ...
        ({(0, 1): NOISE, (2,): NOISE}, "but a noise model with 2"),
        # ... and cannot name one qubit twice.
        ({(0, 0): NOISE}, "repeated qubit"),
    )
    @unpack
    def test_invalid_preparation_noise_is_rejected(self, preparation_noise, message):
        """A key that does not match its map is a mistake, not a silently truncated channel."""
        with self.assertRaisesRegex(ValidationError, message):
            SimulatorOptions(preparation_noise=preparation_noise)
