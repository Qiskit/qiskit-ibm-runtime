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

import numpy as np

from qiskit.circuit import QuantumCircuit, Parameter
from qiskit.circuit.library import RealAmplitudes
from qiskit.primitives import Estimator as TerraEstimator
from qiskit.quantum_info import SparsePauliOp
from qiskit.primitives import BaseEstimator, EstimatorResult

from qiskit_ibm_runtime import Estimator, Session

from ..decorators import run_integration_test
from ..ibm_test_case import IBMIntegrationTestCase
from ..utils import bell


class TestIntegrationEstimator(IBMIntegrationTestCase):
    """Integration tests for Estimator primitive."""

    def setUp(self) -> None:
        super().setUp()
        self.backend = "ibmq_qasm_simulator"

    @run_integration_test
    def test_estimator_session(self, service):
        """Verify if estimator primitive returns expected results"""

        psi1 = RealAmplitudes(num_qubits=2, reps=2)
        psi2 = RealAmplitudes(num_qubits=2, reps=3)

        # pylint: disable=invalid-name
        H1 = SparsePauliOp.from_list([("II", 1), ("IZ", 2), ("XI", 3)])
        H2 = SparsePauliOp.from_list([("IZ", 1)])
        H3 = SparsePauliOp.from_list([("ZI", 1), ("ZZ", 1)])

        with Session(service, self.backend) as session:
            estimator = Estimator(session=session)
            self.assertIsInstance(estimator, BaseEstimator)

            theta1 = [0, 1, 1, 2, 3, 5]
            theta2 = [0, 1, 1, 2, 3, 5, 8, 13]
            theta3 = [1, 2, 3, 4, 5, 6]

            circuits1 = [psi1]
            # calculate [ <psi1(theta1)|H1|psi1(theta1)> ]
            job = estimator.run(circuits=circuits1, observables=[H1], parameter_values=[theta1])
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
            job = estimator.run(circuits=circuits3, observables=[H2], parameter_values=[theta2])
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
    def test_estimator_callback(self, service):
        """Test Estimator callback function."""

        def _callback(job_id_, result_):
            nonlocal ws_result
            ws_result.append(result_)
            nonlocal job_ids
            job_ids.add(job_id_)

        ws_result = []
        job_ids = set()

        bell_circuit = bell()
        obs = SparsePauliOp.from_list([("IZ", 1)])

        with Session(service, self.backend) as session:
            estimator = Estimator(session=session)
            job = estimator.run(
                circuits=[bell_circuit] * 60, observables=[obs] * 60, callback=_callback
            )
            result = job.result()
            self.assertIsInstance(ws_result[-1], dict)
            ws_result_values = np.asarray(ws_result[-1]["values"])
            self.assertTrue((result.values == ws_result_values).all())
            self.assertEqual(len(job_ids), 1)
            self.assertEqual(job.job_id(), job_ids.pop())

    @run_integration_test
    def test_estimator_coeffs(self, service):
        """Verify estimator with same operator different coefficients."""

        cir = QuantumCircuit(2)
        cir.h(0)
        cir.cx(0, 1)
        cir.ry(Parameter("theta"), 0)

        theta_vec = np.linspace(-np.pi, np.pi, 15)

        ## OBSERVABLE
        obs1 = SparsePauliOp(["ZZ", "ZX", "XZ", "XX"], [1, -1, +1, 1])
        obs2 = SparsePauliOp(["ZZ", "ZX", "XZ", "XX"], [1, +1, -1, 1])

        ## TERRA ESTIMATOR
        estimator = TerraEstimator()

        job1 = estimator.run(
            circuits=[cir] * len(theta_vec),
            observables=[obs1] * len(theta_vec),
            parameter_values=[[v] for v in theta_vec],
        )
        job2 = estimator.run(
            circuits=[cir] * len(theta_vec),
            observables=[obs2] * len(theta_vec),
            parameter_values=[[v] for v in theta_vec],
        )

        chsh1_terra = job1.result()
        chsh2_terra = job2.result()

        with Session(service=service, backend=self.backend) as session:
            estimator = Estimator(session=session)

            job1 = estimator.run(
                circuits=[cir] * len(theta_vec),
                observables=[obs1] * len(theta_vec),
                parameter_values=[[v] for v in theta_vec],
            )
            job2 = estimator.run(
                circuits=[cir] * len(theta_vec),
                observables=[obs2] * len(theta_vec),
                parameter_values=[[v] for v in theta_vec],
            )

            chsh1_runtime = job1.result()
            chsh2_runtime = job2.result()

        self.assertTrue(np.allclose(chsh1_terra.values, chsh1_runtime.values, rtol=0.3))
        self.assertTrue(np.allclose(chsh2_terra.values, chsh2_runtime.values, rtol=0.3))

    @run_integration_test
    def test_estimator_no_session(self, service):
        """Test estimator primitive without a session."""
        backend = service.backend(self.backend)
        circ_count = 3

        psi1 = RealAmplitudes(num_qubits=2, reps=2)

        # pylint: disable=invalid-name
        H1 = SparsePauliOp.from_list([("II", 1), ("IZ", 2), ("XI", 3)])

        estimator = Estimator(backend=backend)
        self.assertIsInstance(estimator, BaseEstimator)
        self.assertIsNone(estimator.session)

        theta = [0, 1, 1, 2, 3, 5]
        circuits = [psi1] * circ_count
        # calculate [ <psi1(theta1)|H1|psi1(theta1)> ]
        job = estimator.run(
            circuits=circuits,
            observables=[H1] * circ_count,
            parameter_values=[theta] * circ_count,
        )
        result1 = job.result()
        self.assertIsInstance(result1, EstimatorResult)
        self.assertEqual(len(result1.values), len(circuits))
        self.assertEqual(len(result1.metadata), len(circuits))
        self.assertIsNone(job.session_id)
