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

from math import sqrt

from qiskit.circuit import QuantumCircuit, Gate
from qiskit.circuit.library import RealAmplitudes

from qiskit.primitives import BaseSampler, SamplerResult
from qiskit.result import QuasiDistribution
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit.providers.exceptions import QiskitBackendNotFoundError

from qiskit_ibm_runtime import Sampler, Session
from qiskit_ibm_runtime.exceptions import RuntimeJobFailureError

from ..decorators import run_integration_test
from ..ibm_test_case import IBMIntegrationTestCase
from ..utils import bell


class TestIntegrationIBMSampler(IBMIntegrationTestCase):
    """Integration tests for Sampler primitive."""

    def setUp(self) -> None:
        super().setUp()
        self.bell = bell()
        self.backend = "ibmq_qasm_simulator"

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
        backend = service.backend(self.backend)
        pm = generate_preset_pass_manager(optimization_level=1, target=backend.target)

        with Session(service, self.backend) as session:
            sampler = Sampler(session=session)
            self.assertIsInstance(sampler, BaseSampler)

            circuits0 = pm.run([pqc, pqc, pqc2])
            result = sampler.run(
                circuits=circuits0,
                parameter_values=[theta1, theta2, theta3],
            ).result()
            self.assertIsInstance(result, SamplerResult)
            self.assertEqual(len(result.quasi_dists), len(circuits0))
            self.assertEqual(len(result.metadata), len(circuits0))

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

    @run_integration_test
    def test_sampler_optimization_level(self, service):
        """Test transpiler optimization level is properly mapped."""
        with Session(service, self.backend) as session:
            sampler = Sampler(session=session, options={"optimization_level": 1})
            shots = 1000
            result = sampler.run(self.bell, shots=shots).result()
            self.assertEqual(result.quasi_dists[0].shots, shots)
            self.assertAlmostEqual(
                result.quasi_dists[0]._stddev_upper_bound, sqrt(1 / shots), delta=0.1
            )
            self.assertAlmostEqual(result.quasi_dists[0][3], 0.5, delta=0.1)
            self.assertAlmostEqual(result.quasi_dists[0][0], 0.5, delta=0.1)

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
            ws_result_quasi = [QuasiDistribution(quasi) for quasi in ws_result[-1]["quasi_dists"]]
            self.assertEqual(result.quasi_dists, ws_result_quasi)
            self.assertEqual(len(job_ids), 1)
            self.assertEqual(job.job_id(), job_ids.pop())

    @run_integration_test
    def test_sampler_no_session(self, service):
        """Test sampler without session."""
        backend = service.backend(self.backend)
        sampler = Sampler(backend=backend)
        self.assertIsInstance(sampler, BaseSampler)

        circuits = [self.bell] * 3
        job = sampler.run(circuits=circuits)
        result = job.result()
        self.assertIsInstance(result, SamplerResult)
        self.assertEqual(len(result.quasi_dists), len(circuits))
        self.assertEqual(len(result.metadata), len(circuits))
        for i in range(len(circuits)):
            self.assertAlmostEqual(result.quasi_dists[i][3], 0.5, delta=0.1)
            self.assertAlmostEqual(result.quasi_dists[i][0], 0.5, delta=0.1)
        self.assertIsNone(job.session_id)

    @run_integration_test
    def test_sampler_backend_str(self, service):
        """Test v1 primitive with string as backend."""
        # pylint: disable=unused-argument
        with self.assertRaisesRegex(QiskitBackendNotFoundError, "No backend matches"):
            _ = Sampler(backend="fake_manila")
