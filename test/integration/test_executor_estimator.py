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

"""Integration tests for the EstimatorV2 implementation running through Executor."""

from __future__ import annotations

import numpy as np
from ddt import data, ddt
from qiskit.quantum_info import PauliLindbladMap, SparsePauliOp
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

from qiskit_ibm_runtime.executor_estimator import EstimatorV2
from qiskit_ibm_runtime.options_models.zne import DEFAULT_NOISE_FACTORS

from ..ibm_test_case import IBMIntegrationTestCase
from ..utils import make_mirror_circuit_with_phases


@ddt
class TestEstimator(IBMIntegrationTestCase):
    """An integration test, testing EstimatorV2 implemented through Executor."""

    def setUp(self):
        """Test level setup."""
        super().setUp()
        self.backend = self.service.backend(self.dependencies.qpu)

        self.preset_pass_manager = generate_preset_pass_manager(
            optimization_level=1, target=self.backend.target
        )

        # Cache a list of two pubs:
        # PUB 0 - all-to-all broadcasting, with resulting shape (2,2)
        # PUB 1 - one-to-one broadcasting, with resulting shape (2,)

        circuit = make_mirror_circuit_with_phases(self.backend)
        isa_circuit = self.preset_pass_manager.run(circuit)

        zz_with_offset = SparsePauliOp.from_list([("ZZ", 1.0), ("II", 9.0)]).apply_layout(
            isa_circuit.layout
        )
        xx_with_offset = SparsePauliOp.from_list([("XX", 1.0), ("II", 3.0)]).apply_layout(
            isa_circuit.layout
        )

        self.pubs = [
            # Map all parameter sets to all observables: pub shape (2, 2)
            (
                isa_circuit,
                [[zz_with_offset], [xx_with_offset]],
                [[0, np.pi / 4], [np.pi, 5 * np.pi / 4]],
            ),
            # Map each parameter set to one observable: pub shape (2,)
            (
                isa_circuit,
                [zz_with_offset, xx_with_offset],
                [[0, np.pi / 4], [np.pi, 5 * np.pi / 4]],
            ),
        ]

    def test_vanilla_estimator(self):
        """Test the "vanilla" path (no mitigation) for estimator.

        Tests
        - Job completes without exceptions
        - Correct expectation value shapes
        """
        estimator = EstimatorV2(self.backend)
        results = estimator.run(self.pubs).result()

        # Expect one result per pub:
        self.assertEqual(len(results), 2)

        # 4 Expectation values should have been calculated for full broadcasting:
        self.assertEqual(results[0].data.evs.shape, (2, 2))

        # 2 Expectation values should have been calculated for 1 to 1 parameter mapping:
        self.assertEqual(results[1].data.evs.shape, (2,))

    def test_pec_estimator(self):
        """Test the PEC path for estimator.

        Tests
        - Job completes without exceptions
        - Correct expectation value shapes
        """
        estimator = EstimatorV2(self.backend)
        estimator.options.resilience.pec_mitigation = True

        layers = estimator.find_unique_layers(self.pubs, types="gates")
        estimator.options.resilience.layer_noise_model = [
            (layer, PauliLindbladMap.from_list([("X" * layer.operation.num_qubits, 0.001)]))
            for layer in layers
        ]

        results = estimator.run(self.pubs).result()

        # Expect one result per pub:
        self.assertEqual(len(results), 2)

        # 4 Expectation values should have been calculated for full broadcasting:
        self.assertEqual(results[0].data.evs.shape, (2, 2))

        # 2 Expectation values should have been calculated for 1 to 1 parameter mapping:
        self.assertEqual(results[1].data.evs.shape, (2,))

    @data("gate_folding", "pea")
    def test_zne_estimator(self, amplifier):
        """Test the ZNE path for estimator, parameterized over the noise amplifier.

        Tests
        - Job completes without exceptions
        - Correct shapes for all ZNE-specific data bin fields:
            * ``evs``, ``stds``: pub shape
            * ``evs_noise_factors``, ``stds_noise_factors``,
              ``ensemble_stds_noise_factors``: ``(*pub_shape, num_noise_factors)``
            * ``evs_extrapolated``, ``stds_extrapolated``:
              ``(*pub_shape, num_extrapolators, num_extrapolated_noise_factors)``

        - Correct shape and make-up for all ZNE-specific pub metadata fields:
            * ``extrapolators``: pub shape, only requested extrapolators or `multiple`.
        """
        estimator = EstimatorV2(self.backend)
        estimator.options.resilience.zne_mitigation = True
        estimator.options.resilience.zne.amplifier = amplifier

        if amplifier == "pea":
            layers = estimator.find_unique_layers(self.pubs, types="gates")
            estimator.options.resilience.layer_noise_model = [
                (layer, PauliLindbladMap.from_list([("X" * layer.operation.num_qubits, 0.001)]))
                for layer in layers
            ]

        expected_num_noise_factors = len(DEFAULT_NOISE_FACTORS)
        # ``extrapolated_noise_factors`` defaults to ``[0, *noise_factors]``
        expected_num_extrapolated = expected_num_noise_factors + 1
        expected_num_extrapolators = len(estimator.options.resilience.zne.extrapolator)

        results = estimator.run(self.pubs).result()

        # Expect one result per pub:
        self.assertEqual(len(results), 2)

        for pub_idx, expected_pub_shape in enumerate([(2, 2), (2,)]):
            data_bin = results[pub_idx].data
            metadata = results[pub_idx].metadata

            # evs, stds and selected extrapolators metadata: pub shape only
            self.assertEqual(data_bin.evs.shape, expected_pub_shape)
            self.assertEqual(data_bin.stds.shape, expected_pub_shape)
            self.assertEqual(
                metadata["resilience"]["zne"]["extrapolators"].shape, expected_pub_shape
            )

            # noise-factor arrays: (*pub_shape, num_noise_factors)
            expected_nf_shape = expected_pub_shape + (expected_num_noise_factors,)
            self.assertEqual(data_bin.evs_noise_factors.shape, expected_nf_shape)
            self.assertEqual(data_bin.stds_noise_factors.shape, expected_nf_shape)
            self.assertEqual(data_bin.ensemble_stds_noise_factors.shape, expected_nf_shape)

            # extrapolated arrays: (*pub_shape, num_extrapolators, num_extrapolated_noise_factors)
            expected_extrap_shape = expected_pub_shape + (
                expected_num_extrapolators,
                expected_num_extrapolated,
            )
            self.assertEqual(data_bin.evs_extrapolated.shape, expected_extrap_shape)
            self.assertEqual(data_bin.stds_extrapolated.shape, expected_extrap_shape)

            # Selected extrapolators must be one the requested extrapolators or `multiple`
            allowed = {*estimator.options.resilience.zne.extrapolator, "multiple"}
            self.assertTrue(set(metadata["resilience"]["zne"]["extrapolators"]).issubset(allowed))
