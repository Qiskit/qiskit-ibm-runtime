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

"""Tests for ResilienceOptions."""

from ddt import ddt
from pydantic import ValidationError
from qiskit.circuit import QuantumCircuit
from qiskit.quantum_info import PauliLindbladMap

from qiskit_ibm_runtime.options_models.resilience import ResilienceOptions

from ...ibm_test_case import IBMTestCase


@ddt
class TestResilienceOptionsDefaults(IBMTestCase):
    """Tests for ResilienceOptions default values and basic instantiation."""

    def test_defaults(self):
        """All fields carry their documented default values."""
        opts = ResilienceOptions()
        self.assertIsNone(opts.measure_mitigation)
        self.assertEqual(opts.measure_noise_learning.num_randomizations, "auto")
        self.assertFalse(opts.pec_mitigation)
        self.assertEqual(opts.pec.max_overhead, 100)
        self.assertEqual(opts.pec.noise_gain, "auto")
        self.assertFalse(opts.zne_mitigation)
        self.assertEqual(opts.zne.amplifier, "gate_folding")
        self.assertEqual(opts.zne.noise_factors, "auto")
        self.assertEqual(opts.layer_noise_model, None)

    def test_set_all_options(self):
        """All fields accept explicit non-default values."""
        circuit = QuantumCircuit(2)
        with circuit.box():
            circuit.cx(0, 1)
        _, box = circuit.data
        layer_noise_model = [(box, PauliLindbladMap.identity(num_qubits=1))]
        opts = ResilienceOptions(
            measure_mitigation=False,
            measure_noise_learning={"num_randomizations": 64},
            pec_mitigation=True,
            pec={"max_overhead": 50, "noise_gain": 0.5},
            zne_mitigation=True,
            zne={"amplifier": "gate_folding_front", "noise_factors": [1, 3, 5]},
            layer_noise_model=layer_noise_model,
        )
        self.assertFalse(opts.measure_mitigation)
        self.assertEqual(opts.measure_noise_learning.num_randomizations, 64)
        self.assertTrue(opts.pec_mitigation)
        self.assertEqual(opts.pec.max_overhead, 50)
        self.assertEqual(opts.pec.noise_gain, 0.5)
        self.assertTrue(opts.zne_mitigation)
        self.assertEqual(opts.zne.amplifier, "gate_folding_front")
        self.assertEqual(list(opts.zne.noise_factors), [1, 3, 5])
        self.assertEqual(opts.layer_noise_model, layer_noise_model)

    def test_invalid_layer_noise_model(self):
        """Invalid layer_noise_model values raise ValidationError."""
        circuit = QuantumCircuit(2)
        circuit.x(0)
        with circuit.box():
            circuit.cx(0, 1)
        not_box, box = circuit.data

        options = ResilienceOptions(layer_noise_model=[(box, PauliLindbladMap.identity(2))])
        self.assertEqual(options.layer_noise_model, [(box, PauliLindbladMap.identity(2))])

        with self.assertRaisesRegex(ValidationError, "does not contain a box"):
            ResilienceOptions(layer_noise_model=[(not_box, PauliLindbladMap.identity(2))])

        with self.assertRaisesRegex(ValidationError, "Found instruction with 2"):
            ResilienceOptions(layer_noise_model=[(box, PauliLindbladMap.identity(1))])
