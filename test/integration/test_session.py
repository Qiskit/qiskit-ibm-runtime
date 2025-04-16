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

from unittest import SkipTest, mock

from qiskit.circuit.library import RealAmplitudes
from qiskit.quantum_info import SparsePauliOp

from qiskit.primitives import PrimitiveResult
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

from qiskit_ibm_runtime import Session, Batch, SamplerV2, EstimatorV2
from qiskit_ibm_runtime.exceptions import IBMInputValueError

from ..utils import bell
from ..decorators import run_integration_test, quantum_only
from ..ibm_test_case import IBMIntegrationTestCase


class TestIntegrationSession(IBMIntegrationTestCase):
    """Integration tests for Session."""

    @run_integration_test
    def test_estimator_sampler(self, service):
        """Test calling both estimator and sampler."""
        backend = service.backend(self.dependencies.qpu)

        pm = generate_preset_pass_manager(optimization_level=1, target=backend.target)
        psi1 = pm.run(RealAmplitudes(num_qubits=2, reps=2))

        # pylint: disable=invalid-name
        H1 = SparsePauliOp.from_list([("II", 1), ("IZ", 2), ("XI", 3)]).apply_layout(psi1.layout)
        theta1 = [0, 1, 1, 2, 3, 5]

        with Session(backend=backend) as session:
            estimator = EstimatorV2(mode=session)
            result = estimator.run([(psi1, H1, [theta1])]).result()
            self.assertIsInstance(result, PrimitiveResult)

            sampler = SamplerV2(mode=session)
            result = sampler.run([pm.run(bell())]).result()
            self.assertIsInstance(result, PrimitiveResult)

            result = estimator.run([(psi1, H1, [theta1])]).result()
            self.assertIsInstance(result, PrimitiveResult)
            self.assertEqual(result[0].metadata["shots"], 4096)

            result = sampler.run([pm.run(bell())]).result()
            self.assertIsInstance(result, PrimitiveResult)
            session.close()

    @run_integration_test
    @quantum_only
    def test_using_correct_instance(self, service):
        """Test the instance used when filtering backends is honored."""
        instance = self.dependencies.instance
        backend = service.backend(self.dependencies.qpu, self.dependencies.instance)
        pm = generate_preset_pass_manager(optimization_level=1, target=backend.target)
        with Session(backend=backend) as session:
            sampler = SamplerV2(mode=session)
            job = sampler.run([pm.run(bell())])
            self.assertEqual(instance, backend._instance)
            self.assertEqual(instance, job.backend()._instance)

    @run_integration_test
    def test_session_from_id(self, service):
        """Test creating a session from a given id"""
        backend = service.backend(self.dependencies.qpu)
        if backend.configuration().simulator:
            raise SkipTest("No proper backends available")
        pm = generate_preset_pass_manager(backend=backend, optimization_level=1)
        isa_circuit = pm.run([bell()])
        with Session(backend=backend) as session:
            sampler = SamplerV2(mode=session)
            sampler.run(isa_circuit)

        with mock.patch.object(service._api_client, "create_session") as mock_create_session:
            new_session = Session.from_id(session_id=session._session_id, service=service)
            mock_create_session.assert_not_called()

        self.assertEqual(session._session_id, new_session._session_id)
        self.assertTrue(new_session._active)
        new_session.close()
        self.assertFalse(new_session._active)

        with self.assertRaises(IBMInputValueError):
            Batch.from_id(session_id=session._session_id, service=service)
