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

"""Tests for SamplerOptions."""

from unittest.mock import patch

from ddt import data, ddt
from pydantic import ValidationError
from qiskit.transpiler import CouplingMap

from qiskit_ibm_runtime.options_models.sampler import SamplerOptions
from qiskit_ibm_runtime.options_models.simulator import SimulatorOptions

from ...ibm_test_case import IBMTestCase


@ddt
class TestSimulatorOptions(IBMTestCase):
    """Tests for SimulatorOptions in SamplerOptions."""

    def test_simulator_options_default(self):
        """Test that simulator options have correct defaults."""
        options = SamplerOptions()

        self.assertIsNone(options.simulator.noise_model)
        self.assertIsNone(options.simulator.seed_simulator)
        self.assertIsNone(options.simulator.coupling_map)
        self.assertIsNone(options.simulator.basis_gates)

    @data([[0, 1], [1, 2]], CouplingMap([[0, 1], [1, 2]]))
    def test_coupling_map_valid(self, coupling_map):
        """Test setting coupling map."""
        options = SamplerOptions()
        options.simulator.coupling_map = coupling_map

        self.assertEqual(options.simulator.coupling_map, coupling_map)

    @data("bad_input", [1, 2, 3], [[0, 1], [-1, 0]])
    def test_coupling_map_invalid_type_raises(self, input):
        """Non-list, non-CouplingMap, non-None value should raise ValidationError."""
        with self.assertRaises(ValidationError):
            SimulatorOptions(coupling_map=input)

    def test_noise_model_invalid_type_no_aer_raises(self):
        """Passing a non-dict noise_model raises when Aer is not installed."""
        with patch("qiskit_ibm_runtime.options_models.simulator.optionals.HAS_AER", False):
            with self.assertRaises(ValidationError):
                SimulatorOptions(noise_model=object())

    def test_noise_model_invalid_type_with_aer_raises(self):
        """A non-dict, non-AerNoiseModel value raises ValidationError."""
        with self.assertRaises(ValidationError):
            SimulatorOptions(noise_model=12345)
