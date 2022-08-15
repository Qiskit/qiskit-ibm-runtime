# This code is part of Qiskit.
#
# (C) Copyright IBM 2022.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Integration tests for Estimator primitive."""

from qiskit.circuit.library import RealAmplitudes
from qiskit.quantum_info import SparsePauliOp

from qiskit_ibm_runtime import Estimator, EstimatorResult, BaseEstimator, Session

from ..decorators import run_integration_test
from ..ibm_test_case import IBMIntegrationTestCase


class TestIntegrationEstimator(IBMIntegrationTestCase):
    """Integration tests for Estimator primitive."""

    @run_integration_test
    def test_estimator_session(self, service):
        """Verify if estimator primitive returns expected results"""

        options = {"backend": "ibmq_qasm_simulator"}

        psi1 = RealAmplitudes(num_qubits=2, reps=2)
        psi2 = RealAmplitudes(num_qubits=2, reps=3)

        # pylint: disable=invalid-name
        H1 = SparsePauliOp.from_list([("II", 1), ("IZ", 2), ("XI", 3)])
        H2 = SparsePauliOp.from_list([("IZ", 1)])
        H3 = SparsePauliOp.from_list([("ZI", 1), ("ZZ", 1)])

        with Session(service) as session:
            estimator = Estimator(session=session, options=options)
            self.assertIsInstance(estimator, BaseEstimator)

            theta1 = [0, 1, 1, 2, 3, 5]
            theta2 = [0, 1, 1, 2, 3, 5, 8, 13]
            theta3 = [1, 2, 3, 4, 5, 6]

            circuits1 = [psi1]
            # calculate [ <psi1(theta1)|H1|psi1(theta1)> ]
            job = estimator.run(
                circuits=circuits1, observables=[H1], parameter_values=[theta1]
            )
            result1 = job.result()
            self.assertIsInstance(result1, EstimatorResult)
            self.assertEqual(len(result1.values), len(circuits1))
            self.assertEqual(len(result1.metadata), len(circuits1))

            circuits2 = circuits1 * 2
            # calculate [ <psi1(theta1)|H2|psi1(theta1)>, <psi1(theta1)|H3|psi1(theta1)> ]
            job = estimator.run(
                circuits=circuits2, observables=[H2, H3], parameter_values=[theta1] * 2
            )
            result2 = job.result()
            self.assertIsInstance(result2, EstimatorResult)
            self.assertEqual(len(result2.values), len(circuits2))
            self.assertEqual(len(result2.metadata), len(circuits2))

            circuits3 = [psi2]
            # calculate [ <psi2(theta2)|H2|psi2(theta2)> ]
            job = estimator.run(
                circuits=circuits3, observables=[H2], parameter_values=[theta2]
            )
            result3 = job.result()
            self.assertIsInstance(result3, EstimatorResult)
            self.assertEqual(len(result3.values), len(circuits3))
            self.assertEqual(len(result3.metadata), len(circuits3))

            # calculate [ <psi1(theta1)|H1|psi1(theta1)>, <psi1(theta3)|H1|psi1(theta3)> ]
            job = estimator.run(
                circuits=circuits2,
                observables=[H1, H1],
                parameter_values=[theta1, theta3],
            )
            result4 = job.result()
            self.assertIsInstance(result4, EstimatorResult)
            self.assertEqual(len(result4.values), len(circuits2))
            self.assertEqual(len(result4.metadata), len(circuits2))

            circuits5 = [psi1, psi2, psi1]
            # calculate [ <psi1(theta1)|H1|psi1(theta1)>,
            #             <psi2(theta2)|H2|psi2(theta2)>,
            #             <psi1(theta3)|H3|psi1(theta3)> ]
            job = estimator.run(
                circuits=circuits5,
                observables=[H1, H2, H3],
                parameter_values=[theta1, theta2, theta3],
            )
            result5 = job.result()
            self.assertIsInstance(result5, EstimatorResult)
            self.assertEqual(len(result5.values), len(circuits5))
            self.assertEqual(len(result5.metadata), len(circuits5))

    @run_integration_test
    def test_estimator_primitive(self, service):
        """Test to verify that estimator as a primitive still works."""

        options = {"backend": "ibmq_qasm_simulator"}

        psi1 = RealAmplitudes(num_qubits=2, reps=2)
        psi2 = RealAmplitudes(num_qubits=2, reps=3)

        # pylint: disable=invalid-name
        H1 = SparsePauliOp.from_list([("II", 1), ("IZ", 2), ("XI", 3)])
        H2 = SparsePauliOp.from_list([("IZ", 1)])
        H3 = SparsePauliOp.from_list([("ZI", 1), ("ZZ", 1)])

        with Estimator(
            circuits=[psi1, psi2],
            observables=[H1, H2, H3],
            service=service,
            options=options,
        ) as estimator:
            self.assertIsInstance(estimator, BaseEstimator)

            theta1 = [0, 1, 1, 2, 3, 5]
            theta2 = [0, 1, 1, 2, 3, 5, 8, 13]
            theta3 = [1, 2, 3, 4, 5, 6]

            circuits1 = [0]
            # calculate [ <psi1(theta1)|H1|psi1(theta1)> ]
            result1 = estimator(circuits1, [0], [theta1])
            self.assertIsInstance(result1, EstimatorResult)
            self.assertEqual(len(result1.values), len(circuits1))
            self.assertEqual(len(result1.metadata), len(circuits1))

            circuits2 = [0, 0]
            # calculate [ <psi1(theta1)|H2|psi1(theta1)>, <psi1(theta1)|H3|psi1(theta1)> ]
            result2 = estimator(circuits2, [1, 2], [theta1] * 2)
            self.assertIsInstance(result2, EstimatorResult)
            self.assertEqual(len(result2.values), len(circuits2))
            self.assertEqual(len(result2.metadata), len(circuits2))

            circuits3 = [psi2]
            # calculate [ <psi2(theta2)|H2|psi2(theta2)> ]
            result3 = estimator(circuits3, [H2], [theta2])
            self.assertIsInstance(result3, EstimatorResult)
            self.assertEqual(len(result3.values), len(circuits3))
            self.assertEqual(len(result3.metadata), len(circuits3))

            circuits4 = [psi1, psi1]
            # calculate [ <psi1(theta1)|H1|psi1(theta1)>, <psi1(theta3)|H1|psi1(theta3)> ]
            result4 = estimator(circuits4, [H1, H1], [theta1, theta3])
            self.assertIsInstance(result4, EstimatorResult)
            self.assertEqual(len(result4.values), len(circuits4))
            self.assertEqual(len(result4.metadata), len(circuits4))

            circuits5 = [psi1, psi2, psi1]
            # calculate [ <psi1(theta1)|H1|psi1(theta1)>,
            #             <psi2(theta2)|H2|psi2(theta2)>,
            #             <psi1(theta3)|H3|psi1(theta3)> ]
            result5 = estimator(circuits5, [0, 1, 2], [theta1, theta2, theta3])
            self.assertIsInstance(result5, EstimatorResult)
            self.assertEqual(len(result5.values), len(circuits5))
            self.assertEqual(len(result5.metadata), len(circuits5))
