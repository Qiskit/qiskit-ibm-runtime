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

import warnings

from qiskit.circuit.library import RealAmplitudes
from qiskit.quantum_info import SparsePauliOp

from qiskit.primitives import EstimatorResult, SamplerResult
from qiskit.result import Result

from qiskit_ibm_runtime import Estimator, Session, Sampler, Options

from ..utils import bell
from ..decorators import run_integration_test, quantum_only
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
            result = sampler.run(circuits=bell(), shots=200).result()
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

            result = sampler.run(circuits=bell(), shots=400).result()
            self.assertIsInstance(result, SamplerResult)
            self.assertEqual(len(result.quasi_dists), 1)
            self.assertEqual(len(result.metadata), 1)
            self.assertEqual(result.metadata[0]["shots"], 400)
            self.assertAlmostEqual(result.quasi_dists[0][3], 0.5, delta=0.1)
            self.assertAlmostEqual(result.quasi_dists[0][0], 0.5, delta=0.1)
            session.close()

    @run_integration_test
    @quantum_only
    def test_using_correct_instance(self, service):
        """Test the instance used when filtering backends is honored."""
        instance = self.dependencies.instance
        backend = service.backend("ibmq_qasm_simulator", instance=instance)
        with Session(service, backend=backend) as session:
            sampler = Sampler(session=session)
            job = sampler.run(bell(), shots=400)
            self.assertEqual(instance, backend._instance)
            self.assertEqual(instance, job.backend()._instance)

    @run_integration_test
    def test_session_from_id(self, service):
        """Test creating a session from a given id"""
        backend = service.backend("ibmq_qasm_simulator")
        with Session(service, backend=backend) as session:
            sampler = Sampler(session=session)
            job = sampler.run(bell(), shots=400)
            session_id = job.session_id
        new_session = Session.from_id(backend=backend, session_id=session_id)
        sampler = Sampler(session=new_session)
        job = sampler.run(bell(), shots=400)
        self.assertEqual(session_id, job.session_id)


class TestBackendRunInSession(IBMIntegrationTestCase):
    """Integration tests for Backend.run in Session."""

    def test_session_id(self):
        """Test that session_id is updated correctly and maintained throughout the session"""
        backend = self.service.get_backend("ibmq_qasm_simulator")
        backend.open_session()
        self.assertEqual(backend.session.session_id, None)
        self.assertTrue(backend.session.active)
        job1 = backend.run(bell())
        self.assertEqual(job1._session_id, job1.job_id())
        job2 = backend.run(bell())
        self.assertFalse(job2._session_id == job2.job_id())

    def test_backend_run_with_session(self):
        """Test that 'shots' parameter is transferred correctly"""
        shots = 1000
        backend = self.service.backend("ibmq_qasm_simulator")
        backend.open_session()
        result = backend.run(circuits=bell(), shots=shots).result()
        backend.cancel_session()
        self.assertIsInstance(result, Result)
        self.assertEqual(result.results[0].shots, shots)
        self.assertAlmostEqual(
            result.get_counts()["00"], result.get_counts()["11"], delta=shots / 10
        )

    def test_backend_and_primitive_in_session(self):
        """Test Sampler.run and backend.run in the same session."""
        backend = self.service.get_backend("ibmq_qasm_simulator")
        with Session(backend=backend) as session:
            sampler = Sampler(session=session)
            job1 = sampler.run(circuits=bell())
            with warnings.catch_warnings(record=True):
                job2 = backend.run(circuits=bell())
            self.assertEqual(job1.session_id, job1.job_id())
            self.assertIsNone(job2.session_id)
        with backend.open_session() as session:
            with warnings.catch_warnings(record=True):
                sampler = Sampler(backend=backend)
            job1 = backend.run(bell())
            job2 = sampler.run(circuits=bell())
            session_id = session.session_id
            self.assertEqual(session_id, job1.job_id())
            self.assertIsNone(job2.session_id)

    def test_session_cancel(self):
        """Test closing a session"""
        backend = self.service.backend("ibmq_qasm_simulator")
        backend.open_session()
        self.assertTrue(backend.session.active)
        backend.cancel_session()
        self.assertIsNone(backend.session)

    def test_session_close(self):
        """Test closing a session"""
        backend = self.service.backend("ibmq_qasm_simulator")
        backend.open_session()
        self.assertTrue(backend.session.active)
        backend.close_session()
        self.assertIsNone(backend.session)

    def test_run_after_cancel(self):
        """Test running after session is cancelled."""
        backend = self.service.backend("ibmq_qasm_simulator")
        job1 = backend.run(circuits=bell())
        self.assertIsNone(backend.session)
        self.assertIsNone(job1._session_id)

        backend.open_session()
        job2 = backend.run(bell())
        self.assertIsNotNone(job2._session_id)
        backend.cancel_session()

        job3 = backend.run(circuits=bell())
        self.assertIsNone(backend.session)
        self.assertIsNone(job3._session_id)

    def test_session_as_context_manager(self):
        """Test session as a context manager"""
        backend = self.service.backend("ibmq_qasm_simulator")

        with backend.open_session() as session:
            job1 = backend.run(bell())
            session_id = session.session_id
            self.assertEqual(session_id, job1.job_id())
            job2 = backend.run(bell())
            self.assertFalse(session_id == job2.job_id())

    def test_run_after_cancel_as_context_manager(self):
        """Test run after cancel in context manager"""
        backend = self.service.backend("ibmq_qasm_simulator")
        with backend.open_session() as session:
            _ = backend.run(bell())
        self.assertEqual(backend.session, session)
        backend.cancel_session()
        job = backend.run(circuits=bell())
        self.assertIsNone(backend.session)
        self.assertIsNone(job._session_id)
