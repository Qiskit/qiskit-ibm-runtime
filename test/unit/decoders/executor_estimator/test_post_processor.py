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
from ddt import data, ddt, unpack
from qiskit.primitives import PrimitiveResult
from qiskit.primitives.containers.estimator_pub import ObservablesArray
from qiskit.quantum_info import random_pauli_list

from qiskit_ibm_runtime.decoders.executor_estimator.post_processor_v0_1 import (
    estimator_v2_post_processor_v0_1,
    process_expectation_values,
)
from qiskit_ibm_runtime.executor_estimator.utils import get_pauli_basis, unbroadcast_index
from qiskit_ibm_runtime.results.quantum_program import (
    QuantumProgramItemResult,
    QuantumProgramResult,
)


class TestEstimatorV2PostProcessor(unittest.TestCase):
    """Tests for ``estimator_v2_post_processor_v0_1``."""

    def _create_result(
        self,
        meas_data,
        observables,
        measure_bases,
        param_basis_pairs,
        param_shapes,
        circuits_metadata=None,
    ):
        """Helper to create ``QuantumProgramResult`` with common structure."""
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
        result = QuantumProgramResult(
            data=result_data, metadata=None, passthrough_data=passthrough_data
        )
        result._semantic_role = "estimator_v2"
        return result

    def test_post_processor_multiple_pubs(self):
        """Test post-processor with multiple pubs."""
        meas_data_1 = np.zeros((1, 1, 10, 2)).astype(bool)  # All 00 -> +1
        meas_data_2 = np.ones((1, 1, 10, 2)).astype(bool)  # All 11 -> +1

        result_data = [
            QuantumProgramItemResult({"_meas": meas_data_1}),
            QuantumProgramItemResult({"_meas": meas_data_2}),
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
        result = QuantumProgramResult(
            data=result_data, metadata=None, passthrough_data=passthrough_data
        )
        result._semantic_role = "estimator_v2"

        primitive_result = estimator_v2_post_processor_v0_1(result)

        self.assertEqual(len(primitive_result), 2)
        self.assertAlmostEqual(primitive_result[0].data.evs[0], 1.0)
        self.assertAlmostEqual(primitive_result[1].data.evs[0], 1.0)

    def test_post_processor_missing_passthrough_data(self):
        """Test post-processor raises error with missing passthrough data."""
        result = QuantumProgramResult(
            data=QuantumProgramItemResult([{"_meas": np.array([[[False]]])}]),
            metadata=None,
            passthrough_data={},
        )

        with self.assertRaisesRegex(ValueError, "post_processor"):
            estimator_v2_post_processor_v0_1(result)

    def test_post_processor_missing_observables(self):
        """Test post-processor raises error with missing observables."""
        result = QuantumProgramResult(
            data=[QuantumProgramItemResult({"_meas": np.array([[[False]]])})],
            metadata=None,
            passthrough_data={"post_processor": {"version": "v0.1"}},
        )

        with self.assertRaisesRegex(ValueError, "observables"):
            estimator_v2_post_processor_v0_1(result)

    def test_post_processor_empty_result(self):
        """Test post-processor with empty result."""
        result = QuantumProgramResult(data=[], metadata=None, passthrough_data={})
        primitive_result = estimator_v2_post_processor_v0_1(result)

        self.assertIsInstance(primitive_result, PrimitiveResult)
        self.assertEqual(len(primitive_result), 0)

    def test_post_processor_with_circuit_metadata(self):
        """Test post-processor preserves circuit metadata."""
        meas_data = np.array([[[[False, False]] * 10]])
        circuit_metadata = {"experiment_id": "test_123", "custom_field": "value"}

        result = self._create_result(
            meas_data,
            observables=[[{"ZZ": 1.0}]],
            measure_bases=[["ZZ"]],
            param_basis_pairs=[[([], "ZZ")]],
            param_shapes=[[]],
            circuits_metadata=[circuit_metadata],
        )
        primitive_result = estimator_v2_post_processor_v0_1(result)

        pub_result = primitive_result[0]
        self.assertIn("circuit_metadata", pub_result.metadata)
        self.assertEqual(pub_result.metadata["circuit_metadata"], circuit_metadata)


@ddt
class TestProcessExpectationValues(unittest.TestCase):
    """Tests for the ``process_expectation_values`` method."""

    def get_param_basis_pairs(self, observables, param_shape):
        """Helper to compute values for ``param_basis_pairs``.

        Assumes that all the elements of ``observables`` anti-commute, and does not attempt
        to do any grouping.
        """
        param_basis_pairs = []
        for bcast_index in np.ndindex(np.broadcast_shapes(observables.shape, param_shape)):
            param_index = unbroadcast_index(bcast_index, param_shape)
            obs_index = unbroadcast_index(bcast_index, observables.shape)
            observable = observables[obs_index]
            basis = next(iter(observable.keys()))  # observable is a dict from label to coeff
            param_basis_pairs.append([param_index, get_pauli_basis(basis)])
        return param_basis_pairs

    def test_no_meas_creg(self):
        """Test that item result without ``'meas'`` key raises."""
        data = np.random.randint(0, 2, size=(3, 3)).astype(bool)
        item_result = QuantumProgramItemResult({"meas": data})
        with self.assertRaisesRegex(ValueError, "Dedicated creg ``'_meas'``"):
            process_expectation_values(
                item_result=item_result,
                observables=ObservablesArray({"ZZ": 1}),
                param_shape=(),
                param_basis_pairs=[],
            )

    def test_ndim_raises(self):
        """Test that item result with invalid ndim raises."""
        data = np.random.randint(0, 2, size=(3, 3)).astype(bool)
        item_result = QuantumProgramItemResult({"_meas": data})
        with self.assertRaisesRegex(ValueError, "has ``2`` axes"):
            process_expectation_values(
                item_result=item_result,
                observables=ObservablesArray({"ZZ": 1}),
                param_shape=(),
                param_basis_pairs=[],
            )

    def test_non_broadcastable_shapes_raises(self):
        """Test that invalid param shape and observable shape raises."""
        data = np.random.randint(0, 2, size=(1, 1, 1, 10)).astype(bool)
        item_result = QuantumProgramItemResult({"_meas": data})
        with self.assertRaisesRegex(ValueError, "cannot reshape"):
            process_expectation_values(
                item_result=item_result,
                observables=ObservablesArray({"ZZ": 1, "XX": 19}).reshape(1, 2),
                param_shape=(3, 10),
                param_basis_pairs=[],
            )

    def test_evs_1d_obs_no_params(self):
        """Test exp val calculation with a size 1, 1D observable and no params."""
        # Create mock measurement data: 8x 00 (+1), 1x 01 (-1), 1x 10 (-1)
        # num_configs = 1 (one param-basis pair)
        data = np.array([[[[0, 0]] * 8 + [[0, 1], [1, 0]]]]).astype(bool)
        item_result = QuantumProgramItemResult({"_meas": data})

        coeff = 1.3
        evs, _ = process_expectation_values(
            item_result=item_result,
            observables=ObservablesArray({"ZZ": coeff}),
            param_shape=(),
            param_basis_pairs=[((), "ZZ")],
        )

        # Verify result: coeff * (8 * (+1) + 2 * (-1)) = coeff * 6, average =  coeff * 6 / 10
        self.assertAlmostEqual(evs, 0.6 * 1.3)

    def test_evs_2d_obs_no_params(self):
        """Test post-processor with 2D observables and no params."""
        # Two configs: one for ZZ, one for XX (all 00 measurements)
        data = np.zeros((1, 2, 10, 2), dtype=bool)
        item_result = QuantumProgramItemResult({"_meas": data})

        observables = ObservablesArray([{"ZZ": 1.0}, {"XX": 1.0}])
        evs, _ = process_expectation_values(
            item_result=item_result,
            observables=observables,
            param_shape=(),
            param_basis_pairs=[([], "ZZ"), ([], "XX")],
        )

        self.assertTrue(all(evs == np.ones(observables.shape, dtype=bool)))

    @data(
        [(4,), (4,), np.array([0.5, 1, 1, 1])],
        [(2, 2), (2, 2), np.array([[0.5, 1], [1, 1]])],
    )
    @unpack
    def test_evs_values_without_twirling(self, obs_shape, param_shape, expected_evs):
        """Test the correctness of evs when twirling is OFF.

        Expects shapes that broadcast into ``(4,)``.
        """
        # 4 non-commuting observables -> always 4 basis
        obs_like = [{"000": 1 / 2, "111": 1 / 2}, {"+++": 1}, {"rrr": 1}, {"+r0": 1}]
        observables = ObservablesArray(obs_like).reshape(obs_shape)

        data = np.zeros((1, 4, 10, observables.num_qubits), dtype=bool)
        item_result = QuantumProgramItemResult({"_meas": data})

        evs, _ = process_expectation_values(
            item_result=item_result,
            observables=observables,
            param_shape=param_shape,
            param_basis_pairs=self.get_param_basis_pairs(observables, param_shape),
        )
        self.assertTrue(np.all(evs == expected_evs), msg=evs)

    @data(
        [(4,), (4,), np.array([0.5, 1, 1, 1])],
        [(2, 2), (2, 2), np.array([[0.5, 1], [1, 1]])],
    )
    @unpack
    def test_evs_values_with_twirling(self, obs_shape, param_shape, expected_evs):
        """Test the correctness of evs when twirling is ON.

        Expects shapes that broadcast into ``(4,)``.
        """
        # 4 non-commuting observables -> always 4 basis
        obs_like = [{"000": 1 / 2, "111": 1 / 2}, {"+++": 1}, {"rrr": 1}, {"+r0": 1}]
        observables = ObservablesArray(obs_like).reshape(obs_shape)

        data_shape = (18, 4, 10, observables.num_qubits)
        flips = np.random.randint(0, 2, size=data_shape).astype(bool)
        twirled_data = flips
        item_result = QuantumProgramItemResult(
            {"_meas": twirled_data, "measurement_flips._meas": flips}
        )

        evs, _ = process_expectation_values(
            item_result=item_result,
            observables=observables,
            param_shape=param_shape,
            param_basis_pairs=self.get_param_basis_pairs(observables, param_shape),
        )
        self.assertTrue(np.all(evs == expected_evs), msg=evs)

    @data(
        [(2, 2), (2, 2)],
        [(3, 4, 1, 1), (4, 3)],
        [(4, 3), (3, 4, 1, 1)],
        [(4, 3), ()],
        [(), (4, 3)],
    )
    @unpack
    def test_evs_shape_with_non_trivial_broadcasting(self, obs_shape, param_shape):
        """Test shape of evs for params and observables of different shapes."""
        num_qubits = 33
        num_paulis = int(np.prod(obs_shape))
        random_paulis = random_pauli_list(num_qubits, num_paulis, phase=False)
        observables = ObservablesArray(random_paulis).reshape(obs_shape)

        param_basis_pairs = self.get_param_basis_pairs(observables, param_shape)

        num_basis = sum(len(basis) for _param_idx, basis in param_basis_pairs)
        data = np.zeros((1, num_basis, 10, num_qubits), dtype=bool)
        item_result = QuantumProgramItemResult({"_meas": data})

        evs, stds = process_expectation_values(
            item_result=item_result,
            observables=observables,
            param_shape=param_shape,
            param_basis_pairs=param_basis_pairs,
        )

        expected_shape = np.broadcast_shapes(obs_shape, param_shape)
        self.assertTupleEqual(evs.shape, expected_shape)
        self.assertTupleEqual(stds.shape, expected_shape)
