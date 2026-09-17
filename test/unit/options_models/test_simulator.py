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

from ddt import data, ddt
from pydantic import ValidationError
from qiskit.circuit import QuantumCircuit
from qiskit.quantum_info import PauliLindbladMap

from qiskit_ibm_runtime.options_models.simulator import NOISE_POSITIONS, SimulatorOptions

from ...ibm_test_case import IBMTestCase


def _instructions():
    """A two-qubit box instruction and a non-box instruction to build entries from."""
    circuit = QuantumCircuit(2)
    circuit.x(0)
    with circuit.box():
        circuit.cx(0, 1)
    not_box, box = circuit.data
    return box, not_box


BOX, NOT_BOX = _instructions()
NOISE = PauliLindbladMap.identity(2)


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
    )
    def test_entries_are_stored_exactly_as_given(self, entries):
        """Valid entries round-trip unchanged, at either arity and mixed within one list."""
        self.assertEqual(SimulatorOptions(layer_noise_model=entries).layer_noise_model, entries)

    @data("Q", "r", "before", "", "RR")
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
