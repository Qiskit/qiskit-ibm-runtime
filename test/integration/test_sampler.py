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

from qiskit.circuit.library import RealAmplitudes

from qiskit.primitives import BaseSampler, SamplerResult
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit.providers.exceptions import QiskitBackendNotFoundError

from qiskit_ibm_runtime import Sampler, Session

from ..decorators import run_integration_test
from ..ibm_test_case import IBMIntegrationTestCase
from ..utils import bell


class TestIntegrationIBMSampler(IBMIntegrationTestCase):
    """Integration tests for Sampler primitive."""

    def setUp(self) -> None:
        super().setUp()
        self.bell = bell()
        self._backend = self.service.backend(self.dependencies.device)
        pm = generate_preset_pass_manager(optimization_level=1, target=self._backend.target)
        self.isa_circuit = pm.run(self.bell)

    @run_integration_test
    def test_sampler_non_parameterized_circuits(self, service):
        """Test sampler with multiple non-parameterized circuits."""
        # Execute three Bell circuits
        with Session(service, self.dependencies.device) as session:
            sampler = Sampler(session=session)
            self.assertIsInstance(sampler, BaseSampler)
            circuits = [self.isa_circuit] * 3

            circuits1 = circuits
            result1 = sampler.run(circuits=circuits1).result()
            self.assertIsInstance(result1, SamplerResult)
            self.assertEqual(len(result1.quasi_dists), len(circuits1))
            self.assertEqual(len(result1.metadata), len(circuits1))

            circuits2 = [circuits[0], circuits[2]]
            result2 = sampler.run(circuits=circuits2).result()
            self.assertIsInstance(result2, SamplerResult)
            self.assertEqual(len(result2.quasi_dists), len(circuits2))
            self.assertEqual(len(result2.metadata), len(circuits2))

            circuits3 = [circuits[1], circuits[2]]
            result3 = sampler.run(circuits=circuits3).result()
            self.assertIsInstance(result3, SamplerResult)
            self.assertEqual(len(result3.quasi_dists), len(circuits3))
            self.assertEqual(len(result3.metadata), len(circuits3))

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
        pm = generate_preset_pass_manager(optimization_level=1, target=self._backend.target)

        with Session(service, self.dependencies.device) as session:
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
    def test_sampler_optimization_level(self, service):
        """Test transpiler optimization level is properly mapped."""
        with Session(service, self.dependencies.device) as session:
            sampler = Sampler(session=session, options={"optimization_level": 1})
            shots = 1000
            result = sampler.run(self.isa_circuit, shots=shots).result()
            self.assertEqual(result.quasi_dists[0].shots, shots)
            self.assertEqual(len(result.metadata), 1)

    def test_sampler_no_session(self):
        """Test sampler without session."""
        sampler = Sampler(backend=self._backend)
        self.assertIsInstance(sampler, BaseSampler)

        circuits = [self.isa_circuit] * 3
        job = sampler.run(circuits=circuits)
        result = job.result()
        self.assertIsInstance(result, SamplerResult)
        self.assertEqual(len(result.quasi_dists), len(circuits))
        self.assertEqual(len(result.metadata), len(circuits))
        self.assertIsNone(job.session_id)

    def test_sampler_backend_str(self):
        """Test v1 primitive with string as backend."""
        # pylint: disable=unused-argument
        with self.assertRaisesRegex(QiskitBackendNotFoundError, "No backend matches"):
            _ = Sampler(backend="fake_manila")
