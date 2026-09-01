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

from pydantic import ValidationError
from qiskit.circuit import QuantumCircuit
from qiskit.quantum_info import PauliLindbladMap

from qiskit_ibm_runtime.options_models.simulator import SimulatorOptions

from ...ibm_test_case import IBMTestCase


class TestSimulatorOptions(IBMTestCase):
    """Tests for SimulatorOptions."""

    def test_simulator_options_default(self):
        """Test that simulator options have correct defaults."""
        options = SimulatorOptions()

        self.assertEqual(options.angle_decimals, 5)
        self.assertIsNone(options.layer_noise_model)
        self.assertIsNone(options.seed_simulator)
        self.assertTrue(options.warn_absent)

    def test_layer_noise_model_validation(self):
        """Test that the validation for ``layer_noise_model`` works."""
        circuit = QuantumCircuit(2)
        circuit.x(0)
        with circuit.box():
            circuit.cx(0, 1)
        not_box, box = circuit.data

        options = SimulatorOptions(layer_noise_model=[(box, PauliLindbladMap.identity(2))])
        self.assertEqual(options.layer_noise_model, [(box, PauliLindbladMap.identity(2))])

        with self.assertRaisesRegex(ValidationError, "does not contain a box"):
            SimulatorOptions(layer_noise_model=[(not_box, PauliLindbladMap.identity(2))])

        with self.assertRaisesRegex(ValidationError, "Found instruction with 2"):
            SimulatorOptions(layer_noise_model=[(box, PauliLindbladMap.identity(1))])
