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
from ddt import ddt
from qiskit.primitives.base import BaseEstimatorV2  # noqa: TC002
from qiskit.quantum_info import PauliLindbladMap, SparsePauliOp
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from samplomatic import InjectNoise
from samplomatic.utils import get_annotation

from qiskit_ibm_runtime.executor_estimator import EstimatorV2

from ..ibm_test_case import IBMIntegrationTestCase
from ..utils import make_mirror_circuit_with_phases


@ddt
class TestEstimator(IBMIntegrationTestCase):
    """An integration test, testing EstimatorV2 implemented through Executor."""

    estimator_variant: type[BaseEstimatorV2] | None = None

    def setUp(self):
        """Test level setup."""
        super().setUp()
        self.backend = self.service.backend(self.dependencies.qpu)

        self.preset_pass_manager = generate_preset_pass_manager(
            optimization_level=1, target=self.backend.target
        )

    def test_vanilla_estimator(self):
        """Test the "vanilla" path (no mitigation) for estimator.

        Tests
        - Job completes without exceptions
        - Correct expectation value shapes
        """
        circuit = make_mirror_circuit_with_phases(self.backend)
        isa_circuit = self.preset_pass_manager.run(circuit)

        zz_with_offset = SparsePauliOp.from_list([("ZZ", 1.0), ("II", 9.0)]).apply_layout(
            isa_circuit.layout
        )

        xx_with_offset = SparsePauliOp.from_list([("XX", 1.0), ("II", 3.0)]).apply_layout(
            isa_circuit.layout
        )

        estimator = EstimatorV2(self.backend)

        job = estimator.run(
            pubs=[
                # Map all parameter sets to all observables
                (
                    isa_circuit,
                    [[zz_with_offset], [xx_with_offset]],
                    [[0, np.pi / 4], [np.pi, 5 * np.pi / 4]],
                ),
                # Map each parameter set to one observable:
                (
                    isa_circuit,
                    [zz_with_offset, xx_with_offset],
                    [[0, np.pi / 4], [np.pi, 5 * np.pi / 4]],
                ),
            ]
        )

        results = job.result()

        # Expect one result per pub:
        self.assertEqual(len(results), 2)

        # 4 Expectation values should have been calculated for full broadcasting:
        self.assertEqual(results[0].data.evs.shape, (2, 2))

        # 2 Expectation values should have been calculated for 1 to 1 parameter mapping:
        self.assertEqual(results[1].data.evs.shape, (2,))

    def test_pec_estimator(self):
        """Test the PEC path (no mitigation) for estimator.

        Tests
        - Job completes without exceptions
        - Correct expectation value shapes
        """
        circuit = make_mirror_circuit_with_phases(self.backend)
        isa_circuit = self.preset_pass_manager.run(circuit)

        zz_with_offset = SparsePauliOp.from_list([("ZZ", 1.0), ("II", 9.0)]).apply_layout(
            isa_circuit.layout
        )

        xx_with_offset = SparsePauliOp.from_list([("XX", 1.0), ("II", 3.0)]).apply_layout(
            isa_circuit.layout
        )

        pubs = [
            # Map all parameter sets to all observables
            (
                isa_circuit,
                [[zz_with_offset], [xx_with_offset]],
                [[0, np.pi / 4], [np.pi, 5 * np.pi / 4]],
            ),
            # Map each parameter set to one observable:
            (
                isa_circuit,
                [zz_with_offset, xx_with_offset],
                [[0, np.pi / 4], [np.pi, 5 * np.pi / 4]],
            ),
        ]

        estimator = EstimatorV2(self.backend)
        estimator.options.resilience.pec_mitigation = True

        layers = estimator.find_unique_layers(pubs)
        noise_model = {
            annotation.ref: PauliLindbladMap.from_list([("X" * layer.operation.num_qubits, 0.001)])
            for layer in layers
            if (annotation := get_annotation(layer.operation, InjectNoise))
        }
        estimator.options.resilience.noise_model_mapping = noise_model

        job = estimator.run(pubs)
        results = job.result()

        # Expect one result per pub:
        self.assertEqual(len(results), 2)

        # 4 Expectation values should have been calculated for full broadcasting:
        self.assertEqual(results[0].data.evs.shape, (2, 2))

        # 2 Expectation values should have been calculated for 1 to 1 parameter mapping:
        self.assertEqual(results[1].data.evs.shape, (2,))
