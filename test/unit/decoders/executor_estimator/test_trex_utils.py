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

import numpy as np
from qiskit.quantum_info import Pauli, PauliLindbladMap

from qiskit_ibm_runtime.decoders.executor_estimator.trex_utils import (
    calculate_trex_factor,
    get_processed_calibration_data,
)
from qiskit_ibm_runtime.results.quantum_program import QuantumProgramItemResult

from ....ibm_test_case import IBMTestCase


class TestGetProcessedCalibrationData(IBMTestCase):
    """Tests for get_processed_calibration_data function."""

    def test_raises_when_calibration_register_is_missing(self):
        """Test missing TREX calibration data raises ValueError."""
        calibration_result = QuantumProgramItemResult(
            {"measurement_flips._trex_cal": np.zeros((2, 3, 1), dtype=bool)}
        )

        with self.assertRaises(ValueError) as context:
            get_processed_calibration_data(calibration_result)

        self.assertIn("Dedicated TREX calibration circuit is missing", str(context.exception))

    def test_calculates_noise_model_from_calibration_data(self):
        """Test noise model flip rates are computed from flipped calibration data."""
        cal_data = np.array(
            [
                [[False, True], [True, False]],
                [[False, False], [True, True]],
            ],
            dtype=bool,
        )
        cal_flip = np.array(
            [
                [[False, True], [False, False]],
                [[True, False], [False, True]],
            ],
            dtype=bool,
        )
        calibration_result = QuantumProgramItemResult(
            {
                "_trex_cal": cal_data,
                "measurement_flips._trex_cal": cal_flip,
            }
        )

        result = get_processed_calibration_data(calibration_result)

        self.assertIsInstance(result, np.ndarray)
        self.assertEqual(result.all(), np.logical_xor(cal_data, cal_flip).all())


class TestCalculateTrexFactor(IBMTestCase):
    """Tests for calculate_trex_factor function."""

    def test_calculates_factor_based_on_noise_model_for_string_observable(self):
        """Test TREX factor is inverse fidelity of the observable support."""
        error_prop = 0.1
        error_rate = -0.5 * np.log(1.0 - 2.0 * error_prop)
        noise_model = PauliLindbladMap.from_sparse_list([("X", [0], error_rate)], num_qubits=2)

        result = calculate_trex_factor(noise_model, "IZ")
        # in single qubit case, the result should be 1 / (1 - 2*error_prop)
        self.assertEqual(result, 1 / (1 - 2 * error_prop))

    def test_calculates_factor_based_on_noise_model_for_pauli_observable(self):
        """Test non-Z Paulis are converted to Z support on the same qubits."""
        error_prop = 0.1
        error_rate = -0.5 * np.log(1.0 - 2.0 * error_prop)
        error_prop2 = 0.2
        error_rate2 = -0.5 * np.log(1.0 - 2.0 * error_prop2)
        noise_model = PauliLindbladMap.from_sparse_list(
            [("X", [0], error_rate), ("X", [1], error_rate2)], num_qubits=2
        )

        result = calculate_trex_factor(noise_model, Pauli("XY"))
        # in the two qubit case, the result should be the fidelity minus the errors cause by each
        # qubit, plus the errors caused by even number of qubits - which is both qubits
        self.assertEqual(
            result, 1 / (1 - (2 * error_prop + 2 * error_prop2 - 2 * error_prop * 2 * error_prop2))
        )

    def test_identity_observable_has_unit_factor_input_noise_model(self):
        """Test identity observable produces a factor of one."""
        error_prop = 0.3
        error_rate = -0.5 * np.log(1.0 - 2.0 * error_prop)
        noise_model = PauliLindbladMap.from_sparse_list([("X", [0], error_rate)], num_qubits=1)

        result = calculate_trex_factor(noise_model, "I")

        self.assertEqual(result, 1.0)

    def test_calculates_factor_based_on_calibration_circ_for_string_observable(self):
        """Test TREX factor is inverse fidelity of the observable support."""
        cal_data_flipped = np.zeros((10, 100, 2), dtype=bool)
        for rand in range(10):
            cal_data_flipped[rand, rand * 10 : (rand + 1) * 10, :] = True

        result = calculate_trex_factor(cal_data_flipped, "IZ")

        # in single qubit case, the result should be 1 / (1 - 2*error_prop)
        self.assertEqual(result, 1 / (1 - 2 * 0.1))

    def test_calculates_factor_based_on_calibration_circ_for_pauli_observable(self):
        """Test non-Z Paulis are converted to Z support on the same qubits."""
        cal_data_flipped = np.zeros((10, 100, 2), dtype=bool)
        for rand in range(10):
            cal_data_flipped[rand, rand * 10 : (rand + 1) * 10, 0] = True
        # flip the second qubit with no overlap with the first one
        cal_data_flipped[0, 10:30, 1] = True
        for rand in range(1, 8):
            cal_data_flipped[rand, rand * 10 + 10 : (rand + 1) * 10 + 20, 1] = True
        cal_data_flipped[8, 90:100, 1] = True
        cal_data_flipped[8, 0:10, 1] = True
        cal_data_flipped[9, :20, 1] = True

        result = calculate_trex_factor(cal_data_flipped, Pauli("XY"))
        # in the two qubit case, the result should be the fidelity minus the errors cause by each
        # qubit, plus the errors caused by randomization with even number of qubit flips
        # the flips have no overlap so the result should be 1 / (1 - (2*error_prop1 + 2*error_prop2)
        self.assertAlmostEqual(result, 1 / (1 - (2 * 0.1 + 2 * 0.2)))

    def test_identity_observable_has_unit_factor_input_calibration_data(self):
        """Test identity observable produces a factor of one."""
        cal_data_flipped = np.zeros((10, 100, 2), dtype=bool)
        for rand in range(10):
            cal_data_flipped[rand, rand * 10 : (rand + 1) * 10, :] = True

        result = calculate_trex_factor(cal_data_flipped, "I")

        self.assertEqual(result, 1.0)
