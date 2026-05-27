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

"""Unit tests for EstimatorV2 TREX helper functions."""

import unittest

import numpy as np
from qiskit.quantum_info import Pauli, PauliLindbladMap

from qiskit_ibm_runtime.decoders.executor_estimator.trex_utils import (
    calculate_trex_factor,
    calculate_trex_noise_model,
)

from qiskit_ibm_runtime.results.quantum_program import QuantumProgramItemResult


class TestCalculateTrexNoiseModel(unittest.TestCase):
    """Tests for calculate_trex_noise_model function."""

    def test_raises_when_calibration_register_is_missing(self):
        """Test missing TREX calibration data raises ValueError."""
        calibration_result = QuantumProgramItemResult(
            {"measurement_flips._trex_cal": np.zeros((2, 3, 1), dtype=bool)}
        )

        with self.assertRaises(ValueError) as context:
            calculate_trex_noise_model(calibration_result)

        self.assertIn("Dedicated TREX calibration circuit is missing", str(context.exception))

    def test_calculates_noise_model_from_calibration_data(self):
        """Test noise model flip rates are computed from flipped calibration data."""
        calibration_result = QuantumProgramItemResult(
            {
                "_trex_cal": np.array(
                    [
                        [[False, True], [True, False]],
                        [[False, False], [True, True]],
                    ],
                    dtype=bool,
                ),
                "measurement_flips._trex_cal": np.array(
                    [
                        [[False, True], [False, False]],
                        [[True, False], [False, True]],
                    ],
                    dtype=bool,
                ),
            }
        )

        result = calculate_trex_noise_model(calibration_result)

        self.assertIsInstance(result, PauliLindbladMap)
        np.testing.assert_allclose(result.rates, [0.75, 0.0])

    def test_calculates_different_flip_rates_per_qubit(self):
        """Test each qubit flip rate is computed independently."""
        calibration_result = QuantumProgramItemResult(
            {
                "_trex_cal": np.array(
                    [
                        [[False, False], [False, True]],
                        [[True, False], [False, True]],
                    ],
                    dtype=bool,
                ),
                "measurement_flips._trex_cal": np.zeros((2, 2, 2), dtype=bool),
            }
        )

        result = calculate_trex_noise_model(calibration_result)

        np.testing.assert_allclose(result.rates, [0.25, 0.5])


class TestCalculateTrexFactor(unittest.TestCase):
    """Tests for calculate_trex_factor function."""

    def test_calculates_factor_for_string_observable(self):
        """Test TREX factor is inverse fidelity of the observable support."""
        noise_model = PauliLindbladMap.from_sparse_list([("X", [0], 0.1)], num_qubits=2)

        result = calculate_trex_factor(noise_model, "IZ")

        self.assertAlmostEqual(result, np.exp(0.2))

    def test_calculates_factor_for_pauli_observable(self):
        """Test non-Z Paulis are converted to Z support on the same qubits."""
        noise_model = PauliLindbladMap.from_sparse_list(
            [("X", [0], 0.1), ("X", [1], 0.2)], num_qubits=2
        )

        result = calculate_trex_factor(noise_model, Pauli("XY"))

        self.assertAlmostEqual(result, np.exp(0.6))

    def test_identity_observable_has_unit_factor(self):
        """Test identity observable produces a factor of one."""
        noise_model = PauliLindbladMap.from_sparse_list([("X", [0], 0.3)], num_qubits=1)

        result = calculate_trex_factor(noise_model, "I")

        self.assertEqual(result, 1.0)
