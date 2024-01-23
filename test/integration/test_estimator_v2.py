# This code is part of Qiskit.
#
# (C) Copyright IBM 2024.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Integration tests for Estimator V2"""

from qiskit.circuit.library import RealAmplitudes
from qiskit.quantum_info import SparsePauliOp

from qiskit.primitives.containers import PrimitiveResult, PubResult, DataBin

from qiskit_ibm_runtime import EstimatorV2, Session
from ..decorators import run_integration_test
from ..ibm_test_case import IBMIntegrationTestCase


class TestEstimatorV2(IBMIntegrationTestCase):
    """Integration tests for Estimator V2 Primitive."""

    def setUp(self) -> None:
        super().setUp()
        self.backend = "ibmq_qasm_simulator"

    @run_integration_test
    def test_estimator_v2_session(self, service):
        """Verify correct results are returned"""

        psi1 = RealAmplitudes(num_qubits=2, reps=2)
        psi2 = RealAmplitudes(num_qubits=2, reps=3)

        # pylint: disable=invalid-name
        H1 = SparsePauliOp.from_list([("II", 1), ("IZ", 2), ("XI", 3)])
        H2 = SparsePauliOp.from_list([("IZ", 1)])
        H3 = SparsePauliOp.from_list([("ZI", 1), ("ZZ", 1)])

        theta1 = [0, 1, 1, 2, 3, 5]
        theta2 = [0, 1, 1, 2, 3, 5, 8, 13]
        theta3 = [1, 2, 3, 4, 5, 6]

        with Session(service, self.backend) as session:
            estimator = EstimatorV2(session=session)

            job = estimator.run([(psi1, H1, [theta1])])
            result = job.result()
            self.assertIsInstance(result, PrimitiveResult)
            self.assertIsInstance(result[0], PubResult)

            job2 = estimator.run([(psi1, [H1, H3], [theta1, theta3]), (psi2, H2, theta2)])
            result2 = job2.result()
            self.assertIsInstance(result2, PrimitiveResult)
            self.assertIsInstance(result2[0], PubResult)
            self.assertIsInstance(result2[0].data, DataBin)
            self.assertEqual(len(result2[0].data.evs), 2)
            self.assertEqual(len(result2[0].data.stds), 2)

            job3 = estimator.run([(psi1, H1, theta1), (psi2, H2, theta2), (psi1, H3, theta3)])
            result3 = job3.result()
            self.assertIsInstance(result3, PrimitiveResult)
            self.assertIsInstance(result3[2], PubResult)
            self.assertIsInstance(result3[2].data, DataBin)
            self.assertTrue(result3[2].metadata)
