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

"""Unit tests for ResilienceOptions."""

import unittest

from ddt import data, ddt
from pydantic import ValidationError
from qiskit.quantum_info import PauliLindbladMap

from qiskit_ibm_runtime.options_models.resilience_options import ResilienceOptions


class TestResilienceOptionsDefaults(unittest.TestCase):
    """Tests for ResilienceOptions default values and basic instantiation."""

    def test_defaults(self):
        """All fields carry their documented default values."""
        opts = ResilienceOptions()
        self.assertIsNone(opts.measure_mitigation)
        self.assertEqual(opts.measure_noise_learning.num_randomizations, 32)
        self.assertEqual(opts.measure_noise_learning.shots_per_randomization, "auto")
        self.assertFalse(opts.pec_mitigation)
        self.assertEqual(opts.pec.max_overhead, 100)
        self.assertEqual(opts.pec.noise_gain, "auto")
        self.assertFalse(opts.zne_mitigation)
        self.assertEqual(opts.zne.amplifier, "gate_folding")
        self.assertEqual(opts.zne.noise_factors, "auto")
        self.assertIsNone(opts.noise_model_mapping)

    def test_set_all_options(self):
        """All fields accept explicit non-default values."""
        mapping = {
            "layer_0": PauliLindbladMap.identity(num_qubits=1),
            "layer_1": PauliLindbladMap.identity(num_qubits=1),
        }
        opts = ResilienceOptions(
            measure_mitigation=False,
            measure_noise_learning={"num_randomizations": 64, "shots_per_randomization": 1024},
            pec_mitigation=True,
            pec={"max_overhead": 50, "noise_gain": 0.5},
            zne_mitigation=True,
            zne={"amplifier": "gate_folding_front", "noise_factors": [1, 3, 5]},
            noise_model_mapping=mapping,
        )
        self.assertFalse(opts.measure_mitigation)
        self.assertEqual(opts.measure_noise_learning.num_randomizations, 64)
        self.assertEqual(opts.measure_noise_learning.shots_per_randomization, 1024)
        self.assertTrue(opts.pec_mitigation)
        self.assertEqual(opts.pec.max_overhead, 50)
        self.assertEqual(opts.pec.noise_gain, 0.5)
        self.assertTrue(opts.zne_mitigation)
        self.assertEqual(opts.zne.amplifier, "gate_folding_front")
        self.assertEqual(list(opts.zne.noise_factors), [1, 3, 5])
        self.assertEqual(set(opts.noise_model_mapping.keys()), {"layer_0", "layer_1"})


@ddt
class TestNoiseModelMappingValidation(unittest.TestCase):
    """Tests for the noise_model_mapping field validator."""

    @data(
        # (value, fragment expected in the error message)
        "not_a_dict",
        42,
        {0: PauliLindbladMap.identity(num_qubits=1)},  # non-string key
        {"layer_0": "bad_value"},  # non-PauliLindbladMap value
        {"layer_0": None},  # None as a value
    )
    def test_invalid_noise_model_mapping(self, value):
        """Invalid noise_model_mapping values raise ValidationError."""
        with self.assertRaisesRegex(ValidationError, "noise_model_mapping"):
            ResilienceOptions(noise_model_mapping=value)
