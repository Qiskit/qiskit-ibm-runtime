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

"""Unit tests for EstimatorV2 post-processor."""

import unittest
import numpy as np

from qiskit.primitives import PrimitiveResult

from qiskit_ibm_runtime.quantum_program.quantum_program_result import QuantumProgramResult
from qiskit_ibm_runtime.executor_estimator.post_processors.post_processor_v0_1 import (
    estimator_v2_post_processor_v0_1,
)
from qiskit_ibm_runtime.utils.estimator_pub_result import EstimatorPubResult


class TestEstimatorV2PostProcessor(unittest.TestCase):
    """Tests for estimator_v2_post_processor_v0_1."""

    def _create_quantum_result(self, meas_data, observables, measure_bases, circuits_metadata=None):
        """Helper to create QuantumProgramResult with common structure."""
        result_data = [{"_meas": meas_data}]
        passthrough_data = {
            "post_processor": {
                "version": "v0.1",
                "circuits_metadata": circuits_metadata or [None],
                "observables": observables,
                "measure_bases": measure_bases,
            },
        }
        quantum_result = QuantumProgramResult(
            data=result_data, metadata=None, passthrough_data=passthrough_data
        )
        quantum_result._semantic_role = "estimator_v2"
        return quantum_result

    def test_post_processor_single_pub_single_observable(self):
        """Test post-processor with single pub and single observable."""
        # Create mock measurement data: 8x 00 (+1), 1x 01 (-1), 1x 10 (-1)
        # Shape: (num_randomizations, num_bases, shots, num_qubits)
        meas_data = np.array([[[[False, False]] * 8 + [[False, True], [True, False]]]])

        quantum_result = self._create_quantum_result(
            meas_data, observables=[[{"ZZ": 1.0}]], measure_bases=[["ZZ"]]
        )
        primitive_result = estimator_v2_post_processor_v0_1(quantum_result)

        # Verify result: 8 * (+1) + 2 * (-1) = 6, average = 6/10 = 0.6
        self.assertIsInstance(primitive_result, PrimitiveResult)
        self.assertEqual(len(primitive_result), 1)
        self.assertIsInstance(primitive_result[0], EstimatorPubResult)
        self.assertAlmostEqual(primitive_result[0].data.evs[0], 0.6)

    def test_post_processor_multiple_observables(self):
        """Test post-processor with multiple observables."""
        # Two bases: Z basis for ZZ, X basis for XX (all 00 measurements)
        meas_data = np.array(
            [
                [
                    [[False, False]] * 10,  # Basis 0 (Z basis)
                    [[False, False]] * 10,  # Basis 1 (X basis)
                ]
            ]
        )

        quantum_result = self._create_quantum_result(
            meas_data, observables=[[{"ZZ": 1.0}, {"XX": 1.0}]], measure_bases=[["ZZ", "XX"]]
        )
        primitive_result = estimator_v2_post_processor_v0_1(quantum_result)

        self.assertEqual(len(primitive_result[0].data.evs), 2)

    def test_post_processor_with_coefficients(self):
        """Test post-processor with observable coefficients."""
        meas_data = np.array([[[[False, False]] * 10]])  # All 00 -> +1

        quantum_result = self._create_quantum_result(
            meas_data, observables=[[{"ZZ": 2.0}]], measure_bases=[["ZZ"]]
        )
        primitive_result = estimator_v2_post_processor_v0_1(quantum_result)

        # Expectation value: 2.0 * 1.0 = 2.0
        self.assertAlmostEqual(primitive_result[0].data.evs[0], 2.0)

    def test_post_processor_multiple_pubs(self):
        """Test post-processor with multiple pubs."""
        meas_data_1 = np.array([[[[False, False]] * 10]])  # All 00 -> +1
        meas_data_2 = np.array([[[[True, True]] * 10]])  # All 11 -> +1

        result_data = [
            {"_meas": meas_data_1},
            {"_meas": meas_data_2},
        ]
        passthrough_data = {
            "post_processor": {
                "version": "v0.1",
                "circuits_metadata": [None, None],
                "observables": [[{"ZZ": 1.0}], [{"ZZ": 1.0}]],
                "measure_bases": [["ZZ"], ["ZZ"]],
            },
        }
        quantum_result = QuantumProgramResult(
            data=result_data, metadata=None, passthrough_data=passthrough_data
        )
        quantum_result._semantic_role = "estimator_v2"

        primitive_result = estimator_v2_post_processor_v0_1(quantum_result)

        self.assertEqual(len(primitive_result), 2)
        self.assertAlmostEqual(primitive_result[0].data.evs[0], 1.0)
        self.assertAlmostEqual(primitive_result[1].data.evs[0], 1.0)

    def test_post_processor_with_parameter_sweep(self):
        """Test post-processor with parameter sweep."""
        # Shape: (num_randomizations, num_param_values, num_bases, shots, num_qubits)
        meas_data = np.array(
            [
                [
                    [[[False, False]] * 5],  # Parameter value 0: all 00
                    [[[True, True]] * 5],  # Parameter value 1: all 11
                ]
            ]
        )

        quantum_result = self._create_quantum_result(
            meas_data, observables=[[{"ZZ": 1.0}]], measure_bases=[["ZZ"]]
        )
        primitive_result = estimator_v2_post_processor_v0_1(quantum_result)

        # Verify shape: param_shape=(2,), obs_shape=(1,) -> broadcast to (2,)
        evs = primitive_result[0].data.evs
        self.assertEqual(evs.shape, (2,))
        self.assertAlmostEqual(evs[0], 1.0)  # All 00 -> +1
        self.assertAlmostEqual(evs[1], 1.0)  # All 11 -> +1

    def test_post_processor_missing_passthrough_data(self):
        """Test post-processor raises error with missing passthrough data."""
        quantum_result = QuantumProgramResult(
            data=[{"_meas": np.array([[[False]]])}],
            metadata=None,
            passthrough_data={},
        )

        with self.assertRaises(ValueError) as context:
            estimator_v2_post_processor_v0_1(quantum_result)
        self.assertIn("post_processor", str(context.exception))

    def test_post_processor_missing_observables(self):
        """Test post-processor raises error with missing observables."""
        quantum_result = QuantumProgramResult(
            data=[{"_meas": np.array([[[False]]])}],
            metadata=None,
            passthrough_data={"post_processor": {"version": "v0.1"}},
        )

        with self.assertRaises(ValueError) as context:
            estimator_v2_post_processor_v0_1(quantum_result)
        self.assertIn("observables", str(context.exception))

    def test_post_processor_empty_result(self):
        """Test post-processor with empty result."""
        quantum_result = QuantumProgramResult(data=[], metadata=None, passthrough_data={})
        primitive_result = estimator_v2_post_processor_v0_1(quantum_result)

        self.assertIsInstance(primitive_result, PrimitiveResult)
        self.assertEqual(len(primitive_result), 0)

    def test_post_processor_with_circuit_metadata(self):
        """Test post-processor preserves circuit metadata."""
        meas_data = np.array([[[[False, False]] * 10]])
        circuit_metadata = {"experiment_id": "test_123", "custom_field": "value"}

        quantum_result = self._create_quantum_result(
            meas_data,
            observables=[[{"ZZ": 1.0}]],
            measure_bases=[["ZZ"]],
            circuits_metadata=[circuit_metadata],
        )
        primitive_result = estimator_v2_post_processor_v0_1(quantum_result)

        pub_result = primitive_result[0]
        self.assertIn("circuit_metadata", pub_result.metadata)
        self.assertEqual(pub_result.metadata["circuit_metadata"], circuit_metadata)

    def test_post_processor_complex_broadcasting_with_checkerboard(self):
        """Test post-processor with complex broadcasting and checkerboard observable pattern."""
        # param_shape = (3, 4, 1, 1), obs_shape = (4, 3)
        # broadcast((3,4,1,1), (4,3)) = (3,4,4,3)

        # Create measurement data:
        # (num_randomizations, 3, 4, 1, 1, num_bases, shots, qubits)
        # Use 1 basis for simplicity (all observables are ZZ)
        meas_data = np.zeros((1, 3, 4, 1, 1, 1, 10, 2), dtype=bool)

        # Fill with a pattern: param (i,j,0,0) gives measurement based on (i+j) % 4
        for i in range(3):
            for j in range(4):
                pattern = (i + j) % 4
                if pattern == 0:  # 00 -> +1
                    meas_data[0, i, j, 0, 0, 0, :, :] = False
                elif pattern == 1:  # 01 -> -1
                    meas_data[0, i, j, 0, 0, 0, :, 0] = False
                    meas_data[0, i, j, 0, 0, 0, :, 1] = True
                elif pattern == 2:  # 10 -> -1
                    meas_data[0, i, j, 0, 0, 0, :, 0] = True
                    meas_data[0, i, j, 0, 0, 0, :, 1] = False
                else:  # 11 -> +1
                    meas_data[0, i, j, 0, 0, 0, :, :] = True

        result_data = [{"_meas": meas_data}]

        # Create 4x3 observables array with checkerboard coefficients
        # Coefficient is +1 if (i+j) is even, -1 if odd
        # Need to structure as nested list to get shape (4, 3)
        observables = [
            [
                [{"ZZ": 1.0}, {"ZZ": -1.0}, {"ZZ": 1.0}],  # row 0: +, -, +
                [{"ZZ": -1.0}, {"ZZ": 1.0}, {"ZZ": -1.0}],  # row 1: -, +, -
                [{"ZZ": 1.0}, {"ZZ": -1.0}, {"ZZ": 1.0}],  # row 2: +, -, +
                [{"ZZ": -1.0}, {"ZZ": 1.0}, {"ZZ": -1.0}],  # row 3: -, +, -
            ]
        ]

        passthrough_data = {
            "post_processor": {
                "version": "v0.1",
                "circuits_metadata": [None],
                "observables": observables,
                "measure_bases": [["ZZ"]],
            },
        }

        quantum_result = QuantumProgramResult(
            data=result_data, metadata=None, passthrough_data=passthrough_data
        )
        quantum_result._semantic_role = "estimator_v2"

        primitive_result = estimator_v2_post_processor_v0_1(quantum_result)

        # Verify shape: broadcast((3,4,1,1), (4,3)) = (3,4,4,3)
        evs = primitive_result[0].data.evs
        self.assertEqual(evs.shape, (3, 4, 4, 3))

        # Verify specific values: measurement * coefficient
        # measurement: +1 if (param_i+param_j)%4 in {0,3}, -1 if in {1,2}
        # coefficient: +1 if (obs_i+obs_j) even, -1 if odd
        test_cases = [
            ((0, 0, 0, 0), 1.0),  # meas:(0+0)%4=0→+1, coeff:(0+0)even→+1 = +1
            ((0, 1, 0, 1), 1.0),  # meas:(0+1)%4=1→-1, coeff:(0+1)odd→-1 = +1
            ((1, 0, 1, 0), 1.0),  # meas:(1+0)%4=1→-1, coeff:(1+0)odd→-1 = +1
            ((2, 2, 2, 2), 1.0),  # meas:(2+2)%4=0→+1, coeff:(2+2)even→+1 = +1
            ((1, 2, 3, 1), 1.0),  # meas:(1+2)%4=3→+1, coeff:(3+1)even→+1 = +1
            ((0, 2, 1, 2), 1.0),  # meas:(0+2)%4=2→-1, coeff:(1+2)odd→-1 = +1
            ((0, 1, 0, 0), -1.0),  # meas:(0+1)%4=1→-1, coeff:(0+0)even→+1 = -1
        ]
        for indices, expected in test_cases:
            self.assertAlmostEqual(evs[indices], expected)
