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

from qiskit import QuantumCircuit
from qiskit.primitives.containers.estimator_pub import EstimatorPub
from qiskit.quantum_info import SparsePauliOp

from qiskit_ibm_runtime.executor_estimator.trex_utils import create_trex_calibration_circuit
from qiskit_ibm_runtime.options_models.measure_noise_learning_options import (
    MeasureNoiseLearningOptions,
)
from qiskit_ibm_runtime.quantum_program.quantum_program import SamplexItem


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
