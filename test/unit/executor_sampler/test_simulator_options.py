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

"""Tests for SimulatorOptions in executor-based SamplerV2."""

import unittest
from unittest.mock import patch

from ddt import data, ddt
from pydantic import ValidationError
from qiskit.transpiler import CouplingMap

from qiskit_ibm_runtime.executor_sampler import SamplerV2
from qiskit_ibm_runtime.options_models.sampler_options import SamplerOptions
from qiskit_ibm_runtime.options_models.simulator_options import SimulatorOptions
from test.utils import get_mocked_backend


@ddt
class TestSimulatorOptions(unittest.TestCase):
    """Tests for SimulatorOptions in SamplerOptions."""

    def test_simulator_options_default(self):
        """Test that simulator options have correct defaults."""
        options = SamplerOptions()

        self.assertIsNone(options.simulator.noise_model)
        self.assertIsNone(options.simulator.seed_simulator)
        self.assertIsNone(options.simulator.coupling_map)
        self.assertIsNone(options.simulator.basis_gates)

    def test_simulator_options_set_seed(self):
        """Test setting simulator seed."""
        options = SamplerOptions()
        options.simulator.seed_simulator = 42

        self.assertEqual(options.simulator.seed_simulator, 42)

    def test_simulator_options_set_coupling_map(self):
        """Test setting coupling map as list."""
        options = SamplerOptions()
        coupling_map = [[0, 1], [1, 2], [2, 3]]
        options.simulator.coupling_map = coupling_map

        self.assertEqual(options.simulator.coupling_map, CouplingMap(coupling_map))

    def test_simulator_options_set_coupling_map_from_qiskit(self):
        """Test setting coupling map from Qiskit CouplingMap object."""
        options = SamplerOptions()
        qiskit_coupling_map = CouplingMap([[0, 1], [1, 2]])
        options.simulator.coupling_map = qiskit_coupling_map

        self.assertEqual(options.simulator.coupling_map, qiskit_coupling_map)

    def test_simulator_options_set_basis_gates(self):
        """Test setting basis gates."""
        options = SamplerOptions()
        basis_gates = ["u1", "u2", "u3", "cx"]
        options.simulator.basis_gates = basis_gates

        self.assertEqual(options.simulator.basis_gates, basis_gates)

    def test_simulator_options_from_dict(self):
        """Test constructing simulator options from dict."""
        opts_dict = {
            "simulator": {
                "seed_simulator": 123,
                "basis_gates": ["h", "cx", "rz"],
                "coupling_map": [[0, 1], [1, 2]],
            }
        }
        sampler = SamplerV2(mode=get_mocked_backend(), options=opts_dict)

        self.assertEqual(sampler.options.simulator.seed_simulator, 123)
        self.assertEqual(sampler.options.simulator.basis_gates, ["h", "cx", "rz"])
        self.assertEqual(sampler.options.simulator.coupling_map, CouplingMap([[0, 1], [1, 2]]))

    @data("bad_input", [1, 2, 3], [[0, 1], [-1, 0]])
    def test_coupling_map_invalid_type_raises(self, input):
        """Non-list, non-CouplingMap, non-None value should raise ValidationError."""
        with self.assertRaises(ValidationError):
            SimulatorOptions(coupling_map=input)

    def test_noise_model_invalid_type_no_aer_raises(self):
        """Passing a non-dict noise_model raises when Aer is not installed."""
        with patch("qiskit_ibm_runtime.options_models.simulator_options.optionals.HAS_AER", False):
            with self.assertRaises(ValidationError):
                SimulatorOptions(noise_model=object())

    def test_noise_model_invalid_type_with_aer_raises(self):
        """A non-dict, non-AerNoiseModel value raises ValidationError."""
        with self.assertRaises(ValidationError):
            SimulatorOptions(noise_model=12345)
