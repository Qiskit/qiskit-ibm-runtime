# This code is part of Qiskit.
#
# (C) Copyright IBM 2023.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Tests for job functions using real runtime service."""

from qiskit.quantum_info import SparsePauliOp
from qiskit.circuit.library import RealAmplitudes
from qiskit.primitives.containers import PrimitiveResult, PubResult, DataBin, BitArray
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

from qiskit_ibm_runtime import (
    SamplerV2,
    EstimatorV2,
    Batch,
)


from ..ibm_test_case import IBMIntegrationTestCase
from ..decorators import run_integration_test
from ..utils import bell

FIDELITY_THRESHOLD = 0.8
DIFFERENCE_THRESHOLD = 0.35


class TestV2PrimitivesQCTRL(IBMIntegrationTestCase):
    """Integration tests for V2 primitives using QCTRL."""

    def setUp(self) -> None:
        super().setUp()
        self.bell = bell()
        self.backend = self.service.least_busy(simulator=False)

    @run_integration_test
    def test_sampler_v2_qctrl(self, service):
        """Test qctrl bell state with samplerV2"""
        shots = 1

        pm = generate_preset_pass_manager(backend=self.backend, optimization_level=1)
        isa_circuit = pm.run(self.bell)

        with Batch(service, backend=self.backend):
            sampler = SamplerV2()

            result = sampler.run([isa_circuit], shots=shots).result()
            self._verify_sampler_result(result, num_pubs=1)

    @run_integration_test
    def test_estimator_v2_qctrl(self, service):
        """Test simple circuit with estimatorV2 using qctrl."""
        pass_mgr = generate_preset_pass_manager(backend=self.backend, optimization_level=1)

        psi1 = pass_mgr.run(RealAmplitudes(num_qubits=2, reps=2))
        psi2 = pass_mgr.run(RealAmplitudes(num_qubits=2, reps=3))

        # pylint: disable=invalid-name
        H1 = SparsePauliOp.from_list([("II", 1), ("IZ", 2), ("XI", 3)]).apply_layout(psi1.layout)
        H2 = SparsePauliOp.from_list([("IZ", 1)]).apply_layout(psi2.layout)
        H3 = SparsePauliOp.from_list([("ZI", 1), ("ZZ", 1)]).apply_layout(psi1.layout)

        theta1 = [0, 1, 1, 2, 3, 5]
        theta2 = [0, 1, 1, 2, 3, 5, 8, 13]
        theta3 = [1, 2, 3, 4, 5, 6]

        with Batch(service, self.backend):
            estimator = EstimatorV2()

            job = estimator.run([(psi1, H1, [theta1])])
            result = job.result()
            self._verify_estimator_result(result, num_pubs=1, shapes=[(1,)])

            job2 = estimator.run([(psi1, [H1, H3], [theta1, theta3]), (psi2, H2, theta2)])
            result2 = job2.result()
            self._verify_estimator_result(result2, num_pubs=2, shapes=[(2,), (1,)])

            job3 = estimator.run([(psi1, H1, theta1), (psi2, H2, theta2), (psi1, H3, theta3)])
            result3 = job3.result()
            self._verify_estimator_result(result3, num_pubs=3, shapes=[(1,), (1,), (1,)])

    def _verify_sampler_result(self, result, num_pubs, targets=None):
        """Verify result type."""
        self.assertIsInstance(result, PrimitiveResult)
        self.assertIsInstance(result.metadata, dict)
        self.assertEqual(len(result), num_pubs)
        for idx, pub_result in enumerate(result):
            # TODO: We need to update the following test to check `SamplerPubResult`
            # when the server side is upgraded to Qiskit 1.1.
            self.assertIsInstance(pub_result, PubResult)
            self.assertIsInstance(pub_result.data, DataBin)
            self.assertIsInstance(pub_result.metadata, dict)
            if targets:
                self.assertIsInstance(result[idx].data.meas, BitArray)
                self._assert_allclose(result[idx].data.meas, targets[idx])

    def _verify_estimator_result(self, result, num_pubs, shapes):
        """Verify result type."""
        self.assertIsInstance(result, PrimitiveResult)
        self.assertEqual(len(result), num_pubs)
        for idx, pub_result in enumerate(result):
            self.assertIsInstance(pub_result, PubResult)
            self.assertIsInstance(pub_result.data, DataBin)
            self.assertTrue(pub_result.metadata)
            self.assertEqual(pub_result.data.evs.shape, shapes[idx])
            self.assertEqual(pub_result.data.stds.shape, shapes[idx])
