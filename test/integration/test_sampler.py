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

"""Integration tests for Sampler primitive."""

import unittest
from math import sqrt

from qiskit.circuit import QuantumCircuit, Gate
from qiskit.circuit.library import RealAmplitudes
from qiskit.test.reference_circuits import ReferenceCircuits
from qiskit.primitives import BaseSampler, SamplerResult
from qiskit.result import QuasiDistribution

from qiskit_ibm_runtime import Sampler, Session
from qiskit_ibm_runtime.exceptions import RuntimeJobFailureError

from ..decorators import run_integration_test
from ..ibm_test_case import IBMIntegrationTestCase


class TestIntegrationIBMSampler(IBMIntegrationTestCase):
    """Integration tests for Sampler primitive."""

    def setUp(self) -> None:
        super().setUp()
        self.bell = ReferenceCircuits.bell()
        self.backend = "ibmq_qasm_simulator"

    @run_integration_test
    def test_sampler_non_parameterized_single_circuit(self, service):
        """Verify if sampler primitive returns expected results for non-parameterized circuits."""

        # Execute a Bell circuit
        with Session(service, self.backend) as session:
            sampler = Sampler(session=session)
            self.assertIsInstance(sampler, BaseSampler)
            job = sampler.run(circuits=self.bell)
            result = job.result()
            self.assertIsInstance(result, SamplerResult)
            self.assertEqual(len(result.quasi_dists), 1)
            self.assertEqual(len(result.metadata), 1)
            self.assertAlmostEqual(result.quasi_dists[0][3], 0.5, delta=0.1)
            self.assertAlmostEqual(result.quasi_dists[0][0], 0.5, delta=0.1)
            self.assertTrue(session.session_id)
            session.close()

    @run_integration_test
    def test_sampler_non_parameterized_circuits(self, service):
        """Test sampler with multiple non-parameterized circuits."""
        # Execute three Bell circuits
        with Session(service, self.backend) as session:
            sampler = Sampler(session=session)
            self.assertIsInstance(sampler, BaseSampler)
            circuits = [self.bell] * 3

            circuits1 = circuits
            result1 = sampler.run(circuits=circuits1).result()
            self.assertIsInstance(result1, SamplerResult)
            self.assertEqual(len(result1.quasi_dists), len(circuits1))
            self.assertEqual(len(result1.metadata), len(circuits1))
            for i in range(len(circuits1)):
                self.assertAlmostEqual(result1.quasi_dists[i][3], 0.5, delta=0.1)
                self.assertAlmostEqual(result1.quasi_dists[i][0], 0.5, delta=0.1)

            circuits2 = [circuits[0], circuits[2]]
            result2 = sampler.run(circuits=circuits2).result()
            self.assertIsInstance(result2, SamplerResult)
            self.assertEqual(len(result2.quasi_dists), len(circuits2))
            self.assertEqual(len(result2.metadata), len(circuits2))
            for i in range(len(circuits2)):
                self.assertAlmostEqual(result2.quasi_dists[i][3], 0.5, delta=0.1)
                self.assertAlmostEqual(result2.quasi_dists[i][0], 0.5, delta=0.1)

            circuits3 = [circuits[1], circuits[2]]
            result3 = sampler.run(circuits=circuits3).result()
            self.assertIsInstance(result3, SamplerResult)
            self.assertEqual(len(result3.quasi_dists), len(circuits3))
            self.assertEqual(len(result3.metadata), len(circuits3))
            for i in range(len(circuits3)):
                self.assertAlmostEqual(result3.quasi_dists[i][3], 0.5, delta=0.1)
                self.assertAlmostEqual(result3.quasi_dists[i][0], 0.5, delta=0.1)
            session.close()

    @unittest.skip("Skip until data caching is reenabled.")
    @run_integration_test
    def test_sampler_non_parameterized_circuit_caching(self, service):
        """Verify if circuit caching works in sampler primitive
        and returns expected results for non-parameterized circuits."""

        qc1 = QuantumCircuit(2)
        qc1.x(range(2))
        qc1.measure_all()
        qc2 = QuantumCircuit(3)
        qc2.x(range(3))
        qc2.measure_all()
        qc3 = QuantumCircuit(4)
        qc3.x(range(4))
        qc3.measure_all()
        qc4 = QuantumCircuit(5)
        qc4.x(range(5))
        qc4.measure_all()

        with Session(service, self.backend) as session:
            sampler = Sampler(session=session)
            self.assertIsInstance(sampler, BaseSampler)
            job = sampler.run(circuits=[qc1, qc2])
            result = job.result()
            self.assertEqual(len(result.quasi_dists), 2)
            self.assertEqual(len(result.metadata), 2)
            self.assertEqual(result.quasi_dists[0][3], 1)
            self.assertEqual(result.quasi_dists[1][7], 1)

            job = sampler.run(circuits=[qc1])
            result = job.result()
            self.assertEqual(len(result.quasi_dists), 1)
            self.assertEqual(len(result.metadata), 1)
            self.assertEqual(result.quasi_dists[0][3], 1)

            job = sampler.run(circuits=[qc3])
            result = job.result()
            self.assertEqual(len(result.quasi_dists), 1)
            self.assertEqual(len(result.metadata), 1)
            self.assertEqual(result.quasi_dists[0][15], 1)

            job = sampler.run(circuits=[qc1, qc4])
            result = job.result()
            self.assertEqual(len(result.quasi_dists), 2)
            self.assertEqual(len(result.metadata), 2)
            self.assertEqual(result.quasi_dists[0][3], 1)
            self.assertEqual(result.quasi_dists[1][31], 1)
            session.close()

    @unittest.skip("Skip until data caching is reenabled.")
    @run_integration_test
    def test_sampler_non_parameterized_circuit_caching_with_transpilation_options(
        self, service
    ):
        """Verify if circuit caching works in sampler primitive
        by passing correct and incorrect transpilation options."""

        qc1 = QuantumCircuit(2)
        qc1.x(range(2))
        qc1.measure_all()

        with Session(service, self.backend) as session:
            sampler = Sampler(session=session)
            # pass correct initial_layout
            transpilation = {"initial_layout": [0, 1]}
            job = sampler.run(circuits=[qc1], transpilation=transpilation)
            result = job.result()
            self.assertEqual(len(result.quasi_dists), 1)
            self.assertEqual(len(result.metadata), 1)
            self.assertEqual(result.quasi_dists[0][3], 1)

            # pass incorrect initial_layout
            # since a new transpilation option is passed it should not use the
            # cached transpiled circuit from the first run above
            transpilation = {"initial_layout": [0]}
            job = sampler.run(circuits=[qc1], transpilation=transpilation)
            with self.assertRaises(RuntimeJobFailureError):
                job.result()
            session.close()

    @run_integration_test
    def test_sampler_primitive_parameterized_circuits(self, service):
        """Verify if sampler primitive returns expected results for parameterized circuits."""

        # parameterized circuit
        pqc = RealAmplitudes(num_qubits=2, reps=2)
        pqc.measure_all()
        pqc2 = RealAmplitudes(num_qubits=2, reps=3)
        pqc2.measure_all()

        theta1 = [0, 1, 1, 2, 3, 5]
        theta2 = [1, 2, 3, 4, 5, 6]
        theta3 = [0, 1, 2, 3, 4, 5, 6, 7]

        with Session(service, self.backend) as session:
            sampler = Sampler(session=session)
            self.assertIsInstance(sampler, BaseSampler)

            circuits0 = [pqc, pqc, pqc2]
            result = sampler.run(
                circuits=circuits0,
                parameter_values=[theta1, theta2, theta3],
            ).result()
            self.assertIsInstance(result, SamplerResult)
            self.assertEqual(len(result.quasi_dists), len(circuits0))
            self.assertEqual(len(result.metadata), len(circuits0))
            session.close()

    @run_integration_test
    def test_sampler_skip_transpile(self, service):
        """Test skip transpilation option."""
        circ = QuantumCircuit(1, 1)
        custom_gate = Gate("my_custom_gate", 1, [3.14, 1])
        circ.append(custom_gate, [0])
        circ.measure(0, 0)

        with Session(service, self.backend) as session:
            sampler = Sampler(session=session)
            with self.assertRaises(RuntimeJobFailureError) as err:
                sampler.run(circuits=circ, skip_transpilation=True).result()
                # If transpilation not skipped the error would be something about cannot expand.
                self.assertIn("invalid instructions", err.exception.message)
                session.close()

    @run_integration_test
    def test_sampler_optimization_level(self, service):
        """Test transpiler optimization level is properly mapped."""
        with Session(service, self.backend) as session:
            sampler = Sampler(session=session, options={"optimization_level": 3})
            shots = 1000
            result = sampler.run(self.bell, shots=shots).result()
            self.assertEqual(result.quasi_dists[0].shots, shots)
            self.assertAlmostEqual(
                result.quasi_dists[0]._stddev_upper_bound, sqrt(1 / shots), delta=0.1
            )
            self.assertAlmostEqual(result.quasi_dists[0][3], 0.5, delta=0.1)
            self.assertAlmostEqual(result.quasi_dists[0][0], 0.5, delta=0.1)
            session.close()

    @run_integration_test
    def test_sampler_primitive_as_session(self, service):
        """Verify Sampler as a session still works."""

        # parameterized circuit
        pqc = RealAmplitudes(num_qubits=2, reps=2)
        pqc.measure_all()
        pqc2 = RealAmplitudes(num_qubits=2, reps=3)
        pqc2.measure_all()

        theta1 = [0, 1, 1, 2, 3, 5]
        theta2 = [1, 2, 3, 4, 5, 6]
        theta3 = [0, 1, 2, 3, 4, 5, 6, 7]

        with Sampler(
            circuits=[pqc, pqc2],
            service=service,
            options={"backend": "ibmq_qasm_simulator"},
        ) as sampler:
            self.assertIsInstance(sampler, BaseSampler)

            circuits0 = [pqc, pqc, pqc2]
            result = sampler(
                circuits=circuits0,
                parameter_values=[theta1, theta2, theta3],
            )
            self.assertIsInstance(result, SamplerResult)
            self.assertEqual(len(result.quasi_dists), len(circuits0))
            self.assertEqual(len(result.metadata), len(circuits0))

    @run_integration_test
    def test_sampler_callback(self, service):
        """Test Sampler callback function."""

        def _callback(job_id_, result_):
            nonlocal ws_result
            ws_result.append(result_)
            nonlocal job_ids
            job_ids.add(job_id_)

        ws_result = []
        job_ids = set()

        with Session(service, self.backend) as session:
            sampler = Sampler(session=session)
            job = sampler.run(circuits=[self.bell] * 20, callback=_callback)
            result = job.result()

            self.assertIsInstance(ws_result[-1], dict)
            ws_result_quasi = [
                QuasiDistribution(quasi) for quasi in ws_result[-1]["quasi_dists"]
            ]
            self.assertEqual(result.quasi_dists, ws_result_quasi)
            self.assertEqual(len(job_ids), 1)
            self.assertEqual(job.job_id(), job_ids.pop())
            session.close()
