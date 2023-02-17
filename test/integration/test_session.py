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

"""Integration tests for Session."""

from qiskit.circuit.library import RealAmplitudes
from qiskit.quantum_info import SparsePauliOp
from qiskit.test.reference_circuits import ReferenceCircuits
from qiskit.primitives import EstimatorResult, SamplerResult

from qiskit_ibm_runtime import Estimator, Session, Sampler, Options

from ..decorators import run_integration_test
from ..ibm_test_case import IBMIntegrationTestCase


class TestIntegrationSession(IBMIntegrationTestCase):
    """Integration tests for Session."""

    @run_integration_test
    def test_estimator_sampler(self, service):
        """Test calling both estimator and sampler."""

        psi1 = RealAmplitudes(num_qubits=2, reps=2)
        # pylint: disable=invalid-name
        H1 = SparsePauliOp.from_list([("II", 1), ("IZ", 2), ("XI", 3)])
        theta1 = [0, 1, 1, 2, 3, 5]

        options = Options(resilience_level=0)

        with Session(service, backend="ibmq_qasm_simulator") as session:
            estimator = Estimator(session=session, options=options)
            result = estimator.run(
                circuits=[psi1], observables=[H1], parameter_values=[theta1], shots=100
            ).result()
            self.assertIsInstance(result, EstimatorResult)
            self.assertEqual(len(result.values), 1)
            self.assertEqual(len(result.metadata), 1)
            self.assertEqual(result.metadata[0]["shots"], 100)

            sampler = Sampler(session=session, options=options)
            result = sampler.run(circuits=ReferenceCircuits.bell(), shots=200).result()
            self.assertIsInstance(result, SamplerResult)
            self.assertEqual(len(result.quasi_dists), 1)
            self.assertEqual(len(result.metadata), 1)
            self.assertEqual(result.metadata[0]["shots"], 200)
            self.assertAlmostEqual(result.quasi_dists[0][3], 0.5, delta=0.1)
            self.assertAlmostEqual(result.quasi_dists[0][0], 0.5, delta=0.1)

            result = estimator.run(
                circuits=[psi1], observables=[H1], parameter_values=[theta1], shots=300
            ).result()
            self.assertIsInstance(result, EstimatorResult)
            self.assertEqual(len(result.values), 1)
            self.assertEqual(len(result.metadata), 1)
            self.assertEqual(result.metadata[0]["shots"], 300)

            result = sampler.run(circuits=ReferenceCircuits.bell(), shots=400).result()
            self.assertIsInstance(result, SamplerResult)
            self.assertEqual(len(result.quasi_dists), 1)
            self.assertEqual(len(result.metadata), 1)
            self.assertEqual(result.metadata[0]["shots"], 400)
            self.assertAlmostEqual(result.quasi_dists[0][3], 0.5, delta=0.1)
            self.assertAlmostEqual(result.quasi_dists[0][0], 0.5, delta=0.1)
            session.close()
