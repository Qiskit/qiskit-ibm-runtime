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

from qiskit_ibm_runtime.results.quantum_program import QuantumProgramResult
from qiskit_ibm_runtime.executor_estimator.post_processors.post_processor_v0_1 import (
    estimator_v2_post_processor_v0_1,
)
from qiskit_ibm_runtime.results.estimator import EstimatorPubResult


class TestEstimatorV2PostProcessor(unittest.TestCase):
    """Tests for estimator_v2_post_processor_v0_1."""

    def _create_quantum_result(
        self,
        meas_data,
        observables,
        measure_bases,
        param_basis_pairs,
        param_shapes,
        circuits_metadata=None,
    ):
        """Helper to create QuantumProgramResult with common structure."""
        result_data = [{"_meas": meas_data}]
        passthrough_data = {
            "post_processor": {
                "version": "v0.1",
                "circuits_metadata": circuits_metadata or [None],
                "observables": observables,
                "measure_bases": measure_bases,
                "param_basis_pairs": param_basis_pairs,
                "param_shapes": param_shapes,
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
        # num_configs = 1 (one param-basis pair)
        meas_data = np.array([[[[False, False]] * 8 + [[False, True], [True, False]]]])

        quantum_result = self._create_quantum_result(
            meas_data,
            observables=[[{"ZZ": 1.0}]],
            measure_bases=[["ZZ"]],
            param_basis_pairs=[[([], "ZZ")]],  # Single scalar param, single basis
            param_shapes=[[]],  # Scalar parameter shape
        )
        primitive_result = estimator_v2_post_processor_v0_1(quantum_result)

        # Verify result: 8 * (+1) + 2 * (-1) = 6, average = 6/10 = 0.6
        self.assertIsInstance(primitive_result, PrimitiveResult)
        self.assertEqual(len(primitive_result), 1)
        self.assertIsInstance(primitive_result[0], EstimatorPubResult)
        self.assertAlmostEqual(primitive_result[0].data.evs[0], 0.6)

    def test_post_processor_multiple_observables(self):
        """Test post-processor with multiple observables."""
        # Two configs: one for ZZ, one for XX (all 00 measurements)
        meas_data = np.array(
            [
                [
                    [[False, False]] * 10,  # Config 0 (ZZ basis)
                    [[False, False]] * 10,  # Config 1 (XX basis)
                ]
            ]
        )

        quantum_result = self._create_quantum_result(
            meas_data,
            observables=[[{"ZZ": 1.0}, {"XX": 1.0}]],
            measure_bases=[["ZZ", "XX"]],
            param_basis_pairs=[[([], "ZZ"), ([], "XX")]],  # Two observables, scalar params
            param_shapes=[[]],
        )
        primitive_result = estimator_v2_post_processor_v0_1(quantum_result)

        self.assertEqual(len(primitive_result[0].data.evs), 2)

    def test_post_processor_with_coefficients(self):
        """Test post-processor with observable coefficients."""
        # New shape: (num_randomizations, num_configs, shots, num_qubits)
        meas_data = np.array([[[[False, False]] * 10]])  # All 00 -> +1

        quantum_result = self._create_quantum_result(
            meas_data,
            observables=[[{"ZZ": 2.0}]],
            measure_bases=[["ZZ"]],
            param_basis_pairs=[[([], "ZZ")]],
            param_shapes=[[]],
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
                "param_basis_pairs": [[([], "ZZ")], [([], "ZZ")]],
                "param_shapes": [[], []],
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
        # Two configs: one for param 0, one for param 1
        meas_data = np.array(
            [
                [
                    [[False, False]] * 5,  # Config 0: Parameter value 0, all 00
                    [[True, True]] * 5,  # Config 1: Parameter value 1, all 11
                ]
            ]
        )

        quantum_result = self._create_quantum_result(
            meas_data,
            observables=[[{"ZZ": 1.0}]],
            measure_bases=[["ZZ"]],
            param_basis_pairs=[[([0], "ZZ"), ([1], "ZZ")]],  # Two param values
            param_shapes=[[2]],
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
            param_basis_pairs=[[([], "ZZ")]],
            param_shapes=[[]],
            circuits_metadata=[circuit_metadata],
        )
        primitive_result = estimator_v2_post_processor_v0_1(quantum_result)

        pub_result = primitive_result[0]
        self.assertIn("circuit_metadata", pub_result.metadata)
        self.assertEqual(pub_result.metadata["circuit_metadata"], circuit_metadata)
