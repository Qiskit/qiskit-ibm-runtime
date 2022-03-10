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

from qiskit_ibm_runtime import IBMEstimator
from qiskit_ibm_runtime import EstimatorResult
from qiskit_ibm_runtime import BaseEstimator

from ..decorators import run_integration_test
from ..ibm_test_case import IBMIntegrationTestCase


class TestIntegrationIBMEstimator(IBMIntegrationTestCase):
    """Integration tests for Estimator primitive."""

    def _skip_on_legacy(self):
        if self.dependencies.auth == "legacy":
            self.skipTest("Not supported on legacy")

    @run_integration_test
    def test_estimator_primitive(self, service):
        """Verify if estimator primitive returns expected results"""
        self._skip_on_legacy()

        estimator_factory = IBMEstimator(service=service)

        psi1 = RealAmplitudes(num_qubits=2, reps=2)
        psi2 = RealAmplitudes(num_qubits=2, reps=3)

        # pylint: disable=invalid-name
        H1 = SparsePauliOp.from_list([("II", 1), ("IZ", 2), ("XI", 3)])
        H2 = SparsePauliOp.from_list([("IZ", 1)])
        H3 = SparsePauliOp.from_list([("ZI", 1), ("ZZ", 1)])

        with estimator_factory(
            circuits=[psi1, psi2], observables=[H1, H2, H3]
        ) as estimator:
            self.assertIsInstance(estimator, BaseEstimator)

            theta1 = [0, 1, 1, 2, 3, 5]
            theta2 = [0, 1, 1, 2, 3, 5, 8, 13]
            theta3 = [1, 2, 3, 4, 5, 6]

            # calculate [ <psi1(theta1)|H1|psi1(theta1)> ]
            result1 = estimator([0], [0], [theta1])
            self.assertIsInstance(result1, EstimatorResult)

            # calculate [ <psi1(theta1)|H2|psi1(theta1)>, <psi1(theta1)|H3|psi1(theta1)> ]
            result2 = estimator([0, 0], [1, 2], [theta1] * 2)
            self.assertIsInstance(result2, EstimatorResult)

            # calculate [ <psi2(theta2)|H2|psi2(theta2)> ]
            result3 = estimator([1], [1], [theta2])
            self.assertIsInstance(result3, EstimatorResult)

            # calculate [ <psi1(theta1)|H1|psi1(theta1)>, <psi1(theta3)|H1|psi1(theta3)> ]
            result4 = estimator([0, 0], [0, 0], [theta1, theta3])
            self.assertIsInstance(result4, EstimatorResult)

            # calculate [ <psi1(theta1)|H1|psi1(theta1)>,
            #             <psi2(theta2)|H2|psi2(theta2)>,
            #             <psi1(theta3)|H3|psi1(theta3)> ]
            result5 = estimator([0, 1, 0], [0, 1, 2], [theta1, theta2, theta3])
            self.assertIsInstance(result5, EstimatorResult)
