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
    create_pub_result,
    create_pub_result_pec,
    estimator_v2_post_processor_v0_1,
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
        meas_data_2 = np.ones((1, 2, 10, 2)).astype(bool)  # All 11 -> +1 for ZZ and XX configs

        result_data = [
            QuantumProgramItemResult({"_meas": meas_data_1}),
            QuantumProgramItemResult({"_meas": meas_data_2}),
        ]
        passthrough_data = {
            "post_processor": {
                "version": "v0.1",
                "circuits_metadata": [None, None],
                "observables": [[{"ZZ": 1.0}], [{"ZZ": 1.0}, {"XX": 1.0}]],
                "measure_bases": [["ZZ"], ["ZZ", "XX"]],
                "param_basis_pairs": [[([], "ZZ")], [([], "ZZ"), ([], "XX")]],
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
        self.assertAlmostEqual(primitive_result[1].data.evs[1], 1.0)

        # The DataBin shape must track the pub broadcast shape (not default to ``()``).
        self.assertEqual(primitive_result[0].data.shape, (1,))
        self.assertEqual(primitive_result[1].data.shape, (2,))

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

    def test_measure_mitigation_fix_expectation_values(self):
        """Test that measure_mitigation fix expectation values compared to no mitigation.

        This test creates two scenarios:
        1. Without measure_mitigation: raw expectation values from noisy measurements
        2. With measure_mitigation: corrected expectation values using TREX calibration

        The test verifies that the expectation values are fixed after mitigation is being applied.
        """
        # Create measurement data with simulated readout errors
        # For ZZ observable: 00 -> +1, 01 -> -1, 10 -> -1, 11 -> +1
        # Simulate 80% correct readout, 20% bit flip errors
        # Expected ideal: all 00 -> ev = 1.0
        # With errors: 64 correct (00), 16 flipped to 01, 16 flipped to 10, 4 flipped to 11
        # Raw expectation: (64 + 4 - 16 - 16) / 100 = 0.36
        meas_data = np.zeros((1, 1, 100, 2), dtype=bool)
        # Add bit flip errors: flip first bit on 16 shots, second bit on 16 shots, both on 4 shots
        meas_data[0, 0, 64:80, 0] = True  # flip first bit
        meas_data[0, 0, 80:96, 1] = True  # flip second bit
        meas_data[0, 0, 96:100, :] = True  # flip both bits

        # Test 1: Without measure_mitigation
        result_no_mitigation = self._create_result(
            meas_data,
            observables=[[{"ZZ": 1.0}]],
            measure_bases=[["ZZ"]],
            param_basis_pairs=[[([], "ZZ")]],
            param_shapes=[[]],
        )

        primitive_result_no_mitigation = estimator_v2_post_processor_v0_1(result_no_mitigation)
        ev_no_mitigation = primitive_result_no_mitigation[0].data.evs[0]

        # Expected: (64 + 4 - 16 - 16) / 100 = 0.36
        self.assertAlmostEqual(ev_no_mitigation, 0.36, places=5)

        # Test 2: With measure_mitigation
        # Create TREX calibration data that simulates 10% flip rate per qubit
        # Calibration circuit measures |0> states with twirling
        # With 10% flip rate: expect 10% of shots to be |1>
        num_cal_randomizations = 2
        num_cal_shots = 100
        trex_cal_data = np.zeros((num_cal_randomizations, num_cal_shots, 2), dtype=bool)
        trex_cal_flips = np.random.randint(0, 2, size=(num_cal_randomizations, 1, 2), dtype=bool)

        # Simulate 20% flip rate on each qubit
        # First qubit: flip 20 shots per randomization
        trex_cal_data[0, :20, 0] = True
        trex_cal_data[1, 60:80, 0] = True
        # Second qubit: flip 20 shots per randomization with uncorrelated overlap with qubit1
        trex_cal_data[0, 16:36, 1] = True
        trex_cal_data[1, 76:96, 1] = True
        trex_cal_data = np.logical_xor(trex_cal_data, trex_cal_flips)

        result_data_with_mitigation = [
            QuantumProgramItemResult({"_meas": meas_data}),
            QuantumProgramItemResult(
                {
                    "_trex_cal": trex_cal_data,
                    "measurement_flips._trex_cal": trex_cal_flips,
                }
            ),
        ]

        # Passthrough data should only contain metadata for actual pubs, not calibration circuit
        passthrough_data_with_mitigation = {
            "post_processor": {
                "version": "v0.1",
                "circuits_metadata": [None],
                "observables": [[{"ZZ": 1.0}]],
                "measure_bases": [["ZZ"]],
                "param_basis_pairs": [[([], "ZZ")]],
                "param_shapes": [[]],
                "measure_mitigation": "True",
            },
        }

        result_with_mitigation = QuantumProgramResult(
            data=result_data_with_mitigation,
            metadata=None,
            passthrough_data=passthrough_data_with_mitigation,
        )
        result_with_mitigation._semantic_role = "estimator_v2"

        primitive_result_with_mitigation = estimator_v2_post_processor_v0_1(result_with_mitigation)
        ev_with_mitigation = primitive_result_with_mitigation[0].data.evs[0]

        # Verify that after mitigation the expectation value is back to 1
        self.assertAlmostEqual(ev_with_mitigation, 1.0, places=5)

        # Verify that only one pub result is returned (calibration circuit excluded)
        self.assertEqual(
            len(primitive_result_with_mitigation),
            1,
            msg="Should return only one pub result, excluding calibration",
        )

    def test_post_processor_stds_without_twirling(self):
        """Test that stds and ensemble_standard_error are equal without twirling."""
        # Single randomization (no twirling)
        meas_data = np.array([[[[False, False]] * 8 + [[False, True], [True, False]]]])

        result = self._create_result(
            meas_data,
            observables=[[{"ZZ": 1.0}]],
            measure_bases=[["ZZ"]],
            param_basis_pairs=[[([], "ZZ")]],
            param_shapes=[[]],
        )
        primitive_result = estimator_v2_post_processor_v0_1(result)

        # With no twirling (num_randomizations=1), stds and ensemble_standard_error should be equal
        self.assertAlmostEqual(
            primitive_result[0].data.stds[0],
            primitive_result[0].data.ensemble_standard_error[0],
        )

    def test_post_processor_stds_with_twirling(self):
        """Test that stds and ensemble_standard_error differ with twirling."""
        # Multiple randomizations (twirling enabled)
        # Shape: (num_randomizations=3, num_configs=1, shots_per_randomization=10, num_qubits=2)
        meas_data = np.array(
            [
                [[[False, False]] * 8 + [[False, True], [True, False]]],  # Twirl 1: exp_val = 0.6
                [[[False, False]] * 5 + [[False, True]] * 5],  # Twirl 2: exp_val = 0.0
                [[[False, False]] * 7 + [[False, True]] * 3],  # Twirl 3: exp_val = 0.4
            ]
        )

        result = self._create_result(
            meas_data,
            observables=[[{"ZZ": 1.0}]],
            measure_bases=[["ZZ"]],
            param_basis_pairs=[[([], "ZZ")]],
            param_shapes=[[]],
        )
        primitive_result = estimator_v2_post_processor_v0_1(result)

        # Overall expectation value: (6 + 0 + 4) / 30 = 1/3
        self.assertAlmostEqual(primitive_result[0].data.evs[0], 1 / 3)

        # ensemble_standard_error: sqrt(variance / total_shots)
        # variance = 1 - (1/3)^2 = 8/9
        # ensemble_standard_error = sqrt(8/9 / 30) = sqrt(8/270)
        expected_ensemble_std = np.sqrt((1 - (1 / 3) ** 2) / 30)
        self.assertAlmostEqual(
            primitive_result[0].data.ensemble_standard_error[0],
            expected_ensemble_std,
        )

        # stds: sqrt(twirl_variance / num_randomizations)
        twirl_variance = (0.36 + 0.0 + 0.16) / 3 - (1 / 3) ** 2
        expected_stds = np.sqrt(twirl_variance / 3)
        self.assertAlmostEqual(
            primitive_result[0].data.stds[0],
            expected_stds,
        )

        # Verify they are different
        self.assertNotAlmostEqual(
            primitive_result[0].data.stds[0],
            primitive_result[0].data.ensemble_standard_error[0],
        )

    def test_post_processor_with_options_metadata(self):
        """Test that options metadata is properly transferred to primitive result."""
        meas_data = np.array([[[[False, False]] * 10]])

        # Create options metadata
        options_metadata = {
            "twirling": {
                "enable_gates": True,
                "enable_measure": False,
                "num_randomizations": "auto",
                "shots_per_randomization": "auto",
                "strategy": "active-accum",
            },
            "dynamical_decoupling": {
                "enable": True,
                "sequence_type": "XY4",
                "extra_slack_distribution": "middle",
                "scheduling_method": "alap",
            },
            "resilience": {
                "measure_mitigation": True,
                "zne_mitigation": False,
                "pec_mitigation": False,
            },
        }

        result_data = [QuantumProgramItemResult({"_meas": meas_data})]
        passthrough_data = {
            "post_processor": {
                "version": "v0.1",
                "circuits_metadata": [None],
                "observables": [[{"ZZ": 1.0}]],
                "measure_bases": [["ZZ"]],
                "param_basis_pairs": [[([], "ZZ")]],
                "param_shapes": [[]],
                "options": options_metadata,
            },
        }
        result = QuantumProgramResult(
            data=result_data, metadata=None, passthrough_data=passthrough_data
        )
        result._semantic_role = "estimator_v2"

        primitive_result = estimator_v2_post_processor_v0_1(result)

        # Verify primitive-level metadata contains options
        self.assertEqual(primitive_result.metadata, options_metadata)


@ddt
class TestCreatePubResult(unittest.TestCase):
    """Tests for the ``create_pub_result`` function."""

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
            create_pub_result(
                item_result=item_result,
                observables=ObservablesArray({"ZZ": 1}),
                param_shape=(),
                param_basis_pairs=[],
                measure_noise_data=None,
            )

    def test_ndim_raises(self):
        """Test that item result with invalid ndim raises."""
        data = np.random.randint(0, 2, size=(3, 3)).astype(bool)
        item_result = QuantumProgramItemResult({"_meas": data})
        with self.assertRaisesRegex(ValueError, "has ``2`` axes"):
            create_pub_result(
                item_result=item_result,
                observables=ObservablesArray({"ZZ": 1}),
                param_shape=(),
                param_basis_pairs=[],
                measure_noise_data=None,
            )

    def test_non_broadcastable_shapes_raises(self):
        """Test that invalid param shape and observable shape raises."""
        data = np.random.randint(0, 2, size=(1, 1, 1, 10)).astype(bool)
        item_result = QuantumProgramItemResult({"_meas": data})
        with self.assertRaisesRegex(ValueError, "cannot reshape"):
            create_pub_result(
                item_result=item_result,
                observables=ObservablesArray({"ZZ": 1, "XX": 19}).reshape(1, 2),
                param_shape=(3, 10),
                param_basis_pairs=[],
                measure_noise_data=None,
            )

    def test_evs_1d_obs_no_params(self):
        """Test exp val calculation with a size 1, 1D observable and no params."""
        # Create mock measurement data: 8x 00 (+1), 1x 01 (-1), 1x 10 (-1)
        # num_configs = 1 (one param-basis pair)
        data = np.array([[[[0, 0]] * 8 + [[0, 1], [1, 0]]]]).astype(bool)
        item_result = QuantumProgramItemResult({"_meas": data})

        coeff = 1.3
        pub_result = create_pub_result(
            item_result=item_result,
            observables=ObservablesArray({"ZZ": coeff}),
            param_shape=(),
            param_basis_pairs=[((), "ZZ")],
            measure_noise_data=None,
        )
        evs = pub_result.data.evs

        # Verify result: coeff * (8 * (+1) + 2 * (-1)) = coeff * 6, average =  coeff * 6 / 10
        self.assertAlmostEqual(evs, 0.6 * 1.3)

    def test_evs_2d_obs_no_params(self):
        """Test post-processor with 2D observables and no params."""
        # Two configs: one for ZZ, one for XX (all 00 measurements)
        data = np.zeros((1, 2, 10, 2), dtype=bool)
        item_result = QuantumProgramItemResult({"_meas": data})

        observables = ObservablesArray([{"ZZ": 1.0}, {"XX": 1.0}])
        pub_result = create_pub_result(
            item_result=item_result,
            observables=observables,
            param_shape=(),
            param_basis_pairs=[([], "ZZ"), ([], "XX")],
            measure_noise_data=None,
        )
        evs = pub_result.data.evs

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

        pub_result = create_pub_result(
            item_result=item_result,
            observables=observables,
            param_shape=param_shape,
            param_basis_pairs=self.get_param_basis_pairs(observables, param_shape),
            measure_noise_data=None,
        )
        evs = pub_result.data.evs
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

        pub_result = create_pub_result(
            item_result=item_result,
            observables=observables,
            param_shape=param_shape,
            param_basis_pairs=self.get_param_basis_pairs(observables, param_shape),
            measure_noise_data=None,
        )
        evs = pub_result.data.evs
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

        pub_result = create_pub_result(
            item_result=item_result,
            observables=observables,
            param_shape=param_shape,
            param_basis_pairs=param_basis_pairs,
            measure_noise_data=None,
        )

        expected_shape = np.broadcast_shapes(obs_shape, param_shape)
        self.assertTupleEqual(pub_result.data.evs.shape, expected_shape)
        self.assertTupleEqual(pub_result.data.stds.shape, expected_shape)


@ddt
class TestCreatePubResultPec(unittest.TestCase):
    """Tests for the ``create_pub_result_pec`` function."""

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

    def test_missing_pauli_signs_raises_pec(self):
        """Test that missing pauli_signs raises ValueError for PEC."""
        data = np.zeros((1, 2, 10, 2), dtype=bool)
        # Create item result WITHOUT pauli_signs
        item_result = QuantumProgramItemResult({"_meas": data})

        observables = ObservablesArray([{"ZZ": 1.0}, {"XX": 1.0}])
        pec_gamma = 2.0

        with self.assertRaisesRegex(ValueError, "pauli_signs"):
            create_pub_result_pec(
                item_result=item_result,
                observables=observables,
                param_shape=(),
                param_basis_pairs=[((), "ZZ"), ((), "XX")],
                measure_noise_data=None,
                pec_gamma=pec_gamma,
            )

    def test_evs_with_non_zero_pauli_signs_pec(self):
        """Test that non-zero pauli_signs (representing -1) affect expectation values correctly."""
        # Two configs: one for ZZ, one for XX
        # All measurements are 00, which normally gives +1 for both ZZ and XX
        data = np.zeros((1, 2, 10, 2), dtype=bool)

        # Create pauli_signs where:
        # - First config (ZZ): all +1 signs (sum of signs is even, represented as [[0, 0]])
        # - Second config (XX): all -1 signs (sum of signs is odd, represented as [[1, 0]])
        # The signs array has shape (num_randomizations, num_configs, num_error_generators)
        # For simplicity, we use 1 error generator per config
        pauli_signs = np.zeros((1, 2, 1), dtype=np.int8)
        pauli_signs[0, 1, 0] = 1  # Set sign for second config to have odd sum (net -1)

        item_result = QuantumProgramItemResult({"_meas": data, "pauli_signs": pauli_signs})

        observables = ObservablesArray([{"ZZ": 1.0}, {"XX": 1.0}])
        pec_gamma = 2.0

        pub_result = create_pub_result_pec(
            item_result=item_result,
            observables=observables,
            param_shape=(),
            param_basis_pairs=[((), "ZZ"), ((), "XX")],
            measure_noise_data=None,
            pec_gamma=pec_gamma,
        )
        evs = pub_result.data.evs

        # Expected:
        # - ZZ: all measurements are 00 with net +1 signs (even sum) -> ev = +1 * gamma = +2.0
        # - XX: all measurements are 00 with net -1 signs (odd sum) -> ev = -1 * gamma = -2.0
        expected = np.array([2.0, -2.0])
        self.assertTrue(np.allclose(evs, expected), msg=f"Expected {expected}, got {evs}")

    def test_evs_2d_obs_no_params_pec(self):
        """Test post-processor with 2D observables and no params for PEC."""
        # Two configs: one for ZZ, one for XX (all 00 measurements)
        data = np.zeros((1, 2, 10, 2), dtype=bool)
        # Create pauli_signs array with all +1 signs (represented as 0)
        pauli_signs = np.zeros((1, 2, 10), dtype=np.int8)
        item_result = QuantumProgramItemResult({"_meas": data, "pauli_signs": pauli_signs})

        observables = ObservablesArray([{"ZZ": 1.0}, {"XX": 1.0}])
        pec_gamma = 2.0  # Example gamma value

        pub_result = create_pub_result_pec(
            item_result=item_result,
            observables=observables,
            param_shape=(),
            param_basis_pairs=[((), "ZZ"), ((), "XX")],
            measure_noise_data=None,
            pec_gamma=pec_gamma,
        )
        evs = pub_result.data.evs

        # Expected: all measurements are 00, so expectation value is +1, scaled by gamma
        expected = np.ones(observables.shape) * pec_gamma
        self.assertTrue(np.allclose(evs, expected))

    @data(
        [(4,), (4,), np.array([0.5, 1, 1, 1])],
        [(2, 2), (2, 2), np.array([[0.5, 1], [1, 1]])],
    )
    @unpack
    def test_evs_values_without_twirling_pec(self, obs_shape, param_shape, expected_evs_base):
        """Test the correctness of evs when twirling is OFF with PEC.

        Expects shapes that broadcast into ``(4,)``.
        """
        # 4 non-commuting observables -> always 4 basis
        obs_like = [{"000": 1 / 2, "111": 1 / 2}, {"+++": 1}, {"rrr": 1}, {"+r0": 1}]
        observables = ObservablesArray(obs_like).reshape(obs_shape)

        data = np.zeros((1, 4, 10, observables.num_qubits), dtype=bool)
        # Create pauli_signs array with all +1 signs
        pauli_signs = np.zeros((1, 4, 10), dtype=np.int8)
        item_result = QuantumProgramItemResult({"_meas": data, "pauli_signs": pauli_signs})

        pec_gamma = 1.5  # Example gamma value

        pub_result = create_pub_result_pec(
            item_result=item_result,
            observables=observables,
            param_shape=param_shape,
            param_basis_pairs=self.get_param_basis_pairs(observables, param_shape),
            measure_noise_data=None,
            pec_gamma=pec_gamma,
        )
        evs = pub_result.data.evs

        # Expected values should be scaled by gamma
        expected_evs = expected_evs_base * pec_gamma
        self.assertTrue(np.allclose(evs, expected_evs), msg=f"Expected {expected_evs}, got {evs}")

    @data(
        [(4,), (4,), np.array([0.5, 1, 1, 1])],
        [(2, 2), (2, 2), np.array([[0.5, 1], [1, 1]])],
    )
    @unpack
    def test_evs_values_with_twirling_pec(self, obs_shape, param_shape, expected_evs_base):
        """Test the correctness of evs when twirling is ON with PEC.

        Expects shapes that broadcast into ``(4,)``.
        """
        # 4 non-commuting observables -> always 4 basis
        obs_like = [{"000": 1 / 2, "111": 1 / 2}, {"+++": 1}, {"rrr": 1}, {"+r0": 1}]
        observables = ObservablesArray(obs_like).reshape(obs_shape)

        data_shape = (18, 4, 10, observables.num_qubits)
        flips = np.random.randint(0, 2, size=data_shape).astype(bool)
        twirled_data = flips
        # Create pauli_signs array with all +1 signs
        pauli_signs = np.zeros((18, 4, 10), dtype=np.int8)
        item_result = QuantumProgramItemResult(
            {"_meas": twirled_data, "measurement_flips._meas": flips, "pauli_signs": pauli_signs}
        )

        pec_gamma = 2.5  # Example gamma value

        pub_result = create_pub_result_pec(
            item_result=item_result,
            observables=observables,
            param_shape=param_shape,
            param_basis_pairs=self.get_param_basis_pairs(observables, param_shape),
            measure_noise_data=None,
            pec_gamma=pec_gamma,
        )
        evs = pub_result.data.evs

        # Expected values should be scaled by gamma
        expected_evs = expected_evs_base * pec_gamma
        self.assertTrue(np.allclose(evs, expected_evs), msg=f"Expected {expected_evs}, got {evs}")

    @data(
        [(2, 2), (2, 2)],
        [(3, 4, 1, 1), (4, 3)],
        [(4, 3), (3, 4, 1, 1)],
        [(4, 3), ()],
        [(), (4, 3)],
    )
    @unpack
    def test_evs_shape_with_non_trivial_broadcasting_pec(self, obs_shape, param_shape):
        """Test shape of evs for params and observables of different shapes with PEC."""
        num_qubits = 33
        num_paulis = int(np.prod(obs_shape))
        random_paulis = random_pauli_list(num_qubits, num_paulis, phase=False)
        observables = ObservablesArray(random_paulis).reshape(obs_shape)

        param_basis_pairs = self.get_param_basis_pairs(observables, param_shape)

        num_basis = sum(len(basis) for _param_idx, basis in param_basis_pairs)
        data = np.zeros((1, num_basis, 10, num_qubits), dtype=bool)
        # Create pauli_signs array with all +1 signs
        pauli_signs = np.zeros((1, num_basis, 10), dtype=np.int8)
        item_result = QuantumProgramItemResult({"_meas": data, "pauli_signs": pauli_signs})

        pec_gamma = 1.8  # Example gamma value

        pub_result = create_pub_result_pec(
            item_result=item_result,
            observables=observables,
            param_shape=param_shape,
            param_basis_pairs=param_basis_pairs,
            measure_noise_data=None,
            pec_gamma=pec_gamma,
        )

        expected_shape = np.broadcast_shapes(obs_shape, param_shape)
        self.assertTupleEqual(pub_result.data.evs.shape, expected_shape)
        self.assertTupleEqual(pub_result.data.stds.shape, expected_shape)
        self.assertTupleEqual(pub_result.data.ensemble_standard_error.shape, expected_shape)


@ddt
class TestEstimatorV2PostProcessorPEC(unittest.TestCase):
    """Integration tests for PEC dispatch in ``estimator_v2_post_processor_v0_1``."""

    def _create_pec_result(
        self,
        meas_data_list,
        pauli_signs_list,
        observables_list,
        param_basis_pairs_list,
        param_shapes_list,
        pec_gammas,
    ):
        """Helper to create a ``QuantumProgramResult`` with ``pec_gammas`` in passthrough data.

        Args:
            meas_data_list: List of measurement arrays, one per pub.
            pauli_signs_list: List of pauli_signs arrays, one per pub.
            observables_list: List of observable dicts, one per pub.
            param_basis_pairs_list: List of param_basis_pairs, one per pub.
            param_shapes_list: List of param shapes, one per pub.
            pec_gammas: List of gamma floats, one per pub.
        """
        result_data = [
            QuantumProgramItemResult({"_meas": meas, "pauli_signs": signs})
            for meas, signs in zip(meas_data_list, pauli_signs_list)
        ]
        passthrough_data = {
            "post_processor": {
                "version": "v0.1",
                "mitigation": "pec",
                "circuits_metadata": [None] * len(meas_data_list),
                "observables": observables_list,
                "param_basis_pairs": param_basis_pairs_list,
                "param_shapes": param_shapes_list,
                "pec_gammas": pec_gammas,
            },
        }
        result = QuantumProgramResult(
            data=result_data, metadata=None, passthrough_data=passthrough_data
        )
        result._semantic_role = "estimator_v2"
        return result

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
            basis = next(iter(observable.keys()))
            param_basis_pairs.append([param_index, get_pauli_basis(basis)])
        return param_basis_pairs

    def test_post_processor_pec_dispatch_applies_gamma(self):
        """Test that ``pec_gammas`` in passthrough causes gamma scaling on expectation values."""
        # All-zero measurements (00) → raw ZZ ev = +1
        meas_data = np.zeros((1, 1, 10, 2), dtype=bool)
        pauli_signs = np.zeros((1, 1, 1), dtype=np.int8)
        pec_gamma = 2.0

        result = self._create_pec_result(
            meas_data_list=[meas_data],
            pauli_signs_list=[pauli_signs],
            observables_list=[[{"ZZ": 1.0}]],
            param_basis_pairs_list=[[([], "ZZ")]],
            param_shapes_list=[[]],
            pec_gammas=[pec_gamma],
        )

        primitive_result = estimator_v2_post_processor_v0_1(result)

        # raw ev = +1, scaled by gamma = 2.0 → expect 2.0
        self.assertAlmostEqual(primitive_result[0].data.evs[0], pec_gamma)

    def test_post_processor_pec_dispatch_multi_pub_independent_gammas(self):
        """Test that each pub's expectation values are scaled by its own gamma independently."""
        # Pub 0: all-zero measurements → raw ZZ ev = +1, gamma = 1.5 → expected 1.5
        meas_0 = np.zeros((1, 1, 10, 2), dtype=bool)
        signs_0 = np.zeros((1, 1, 1), dtype=np.int8)

        # Pub 1: all-ones measurements (11) → raw ZZ ev = +1, gamma = 3.0 → expected 3.0
        meas_1 = np.ones((1, 1, 10, 2), dtype=bool)
        signs_1 = np.zeros((1, 1, 1), dtype=np.int8)

        result = self._create_pec_result(
            meas_data_list=[meas_0, meas_1],
            pauli_signs_list=[signs_0, signs_1],
            observables_list=[[{"ZZ": 1.0}], [{"ZZ": 1.0}]],
            param_basis_pairs_list=[[([], "ZZ")], [([], "ZZ")]],
            param_shapes_list=[[], []],
            pec_gammas=[1.5, 3.0],
        )

        primitive_result = estimator_v2_post_processor_v0_1(result)

        self.assertEqual(len(primitive_result), 2)
        # Pub 0: raw ev = +1, scaled by 1.5
        self.assertAlmostEqual(primitive_result[0].data.evs[0], 1.5)
        # Pub 1: ZZ on |11> = (-1)(-1) = +1, scaled by 3.0
        self.assertAlmostEqual(primitive_result[1].data.evs[0], 3.0)

    @data(
        [(2, 2), (2, 2)],
        [(3, 4, 1, 1), (4, 3)],
        [(4, 3), (3, 4, 1, 1)],
        [(4, 3), ()],
        [(), (4, 3)],
        [(), ()],
        [(3, 1, 1), (3, 1, 3)],
    )
    @unpack
    def test_pec_post_processor_output_shape(self, obs_shape, param_shape):
        """Test that evs, stds, and ensemble_standard_error have the broadcast shape."""
        num_qubits = 10
        num_paulis = int(np.prod(obs_shape)) if obs_shape else 1
        random_paulis = random_pauli_list(num_qubits, num_paulis, phase=False)
        observables = ObservablesArray(random_paulis).reshape(obs_shape)

        param_basis_pairs = self.get_param_basis_pairs(observables, param_shape)
        num_basis = sum(len(basis) for _param_idx, basis in param_basis_pairs)

        meas_data = np.zeros((1, num_basis, 10, num_qubits), dtype=bool)
        pauli_signs = np.zeros((1, num_basis, 10), dtype=np.int8)

        result = self._create_pec_result(
            meas_data_list=[meas_data],
            pauli_signs_list=[pauli_signs],
            observables_list=[observables.tolist()],
            param_basis_pairs_list=[param_basis_pairs],
            param_shapes_list=[list(param_shape)],
            pec_gammas=[1.8],
        )

        primitive_result = estimator_v2_post_processor_v0_1(result)

        expected_shape = np.broadcast_shapes(obs_shape, param_shape)
        data_bin = primitive_result[0].data
        self.assertTupleEqual(data_bin.evs.shape, expected_shape)
        self.assertTupleEqual(data_bin.stds.shape, expected_shape)
        self.assertTupleEqual(data_bin.ensemble_standard_error.shape, expected_shape)
