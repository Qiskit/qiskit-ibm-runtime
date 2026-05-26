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
from qiskit import QuantumCircuit
from qiskit.primitives.containers.estimator_pub import EstimatorPub
from qiskit.quantum_info import Pauli, PauliLindbladMap, SparsePauliOp

from qiskit_ibm_runtime.executor_estimator.trex_utils import (
    calculate_trex_factor,
    calculate_trex_noise_model,
    create_trex_calibration_circuit,
)
from qiskit_ibm_runtime.options_models.measure_noise_learning_options import (
    MeasureNoiseLearningOptions,
)
from qiskit_ibm_runtime.quantum_program.quantum_program import SamplexItem
from qiskit_ibm_runtime.results.quantum_program import QuantumProgramItemResult


class TestCreateTrexCalibrationCircuit(unittest.TestCase):
    """Tests for create_trex_calibration_circuit function."""

    def test_creates_samplex_item_with_max_qubits_and_requested_randomizations(self):
        """Test calibration circuit shape and size are derived from inputs."""
        circuit1 = QuantumCircuit(2)
        circuit1.h(0)
        circuit1.cx(0, 1)

        circuit2 = QuantumCircuit(3)
        circuit2.x(0)
        circuit2.cx(0, 1)
        circuit2.cx(1, 2)

        pub1 = EstimatorPub.coerce((circuit1, SparsePauliOp.from_list([("ZZ", 1)])))
        pub2 = EstimatorPub.coerce((circuit2, SparsePauliOp.from_list([("ZZZ", 1)])))

        measure_noise_learning = MeasureNoiseLearningOptions()
        measure_noise_learning.num_randomizations = 16

        result = create_trex_calibration_circuit([pub1, pub2], measure_noise_learning)

        self.assertIsInstance(result, SamplexItem)
        self.assertEqual(result.shape, (16,))
        self.assertEqual(result.circuit.num_qubits, 3)
        self.assertIn("_trex_cal", result.circuit.cregs[0].name)

    def test_uses_default_randomizations_when_not_integer(self):
        """Test default randomizations value is used when option is not an integer."""
        circuit = QuantumCircuit(2)
        pub = EstimatorPub.coerce((circuit, SparsePauliOp.from_list([("ZZ", 1)])))

        measure_noise_learning = MeasureNoiseLearningOptions()

        result = create_trex_calibration_circuit([pub], measure_noise_learning)

        self.assertEqual(result.shape, (32,))

    def test_creates_measurement_only_calibration_circuit(self):
        """Test generated TREX circuit contains measurements and no state-preparation gates."""
        circuit = QuantumCircuit(2)
        circuit.h(0)
        circuit.cx(0, 1)
        pub = EstimatorPub.coerce((circuit, SparsePauliOp.from_list([("ZZ", 1)])))

        result = create_trex_calibration_circuit([pub], MeasureNoiseLearningOptions())

        operation_names = {instruction.operation.name for instruction in result.circuit.data}
        self.assertIn("measure", operation_names)
        self.assertFalse({"h", "x", "cx"} & operation_names)


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

# Made with Bob
