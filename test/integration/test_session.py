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

from qiskit.circuit.library import real_amplitudes
from qiskit.quantum_info import SparsePauliOp

from qiskit.circuit import IfElseOp
from qiskit.primitives import PrimitiveResult
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

from qiskit_ibm_runtime import Session, Batch, SamplerV2, EstimatorV2, QiskitRuntimeService
from qiskit_ibm_runtime.exceptions import IBMInputValueError, IBMRuntimeError

from .test_account import _get_service_instance_name_for_crn
from ..utils import bell
from ..decorators import run_integration_test
from ..ibm_test_case import IBMIntegrationTestCase


class TestIntegrationSession(IBMIntegrationTestCase):
    """Integration tests for Session."""

    @run_integration_test
    def test_estimator_sampler(self, service):
        """Test calling both estimator and sampler."""
        backend = service.backend(self.dependencies.qpu)

        pm = generate_preset_pass_manager(optimization_level=1, target=backend.target)
        psi1 = pm.run(real_amplitudes(num_qubits=2, reps=2))

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
    def test_session_from_id(self, service):
        """Test creating a session from a given id"""
        backend = service.backend(self.dependencies.qpu)
        if backend.configuration().simulator:
            raise SkipTest("No proper backends available")
        pm = generate_preset_pass_manager(backend=backend, optimization_level=1)
        isa_circuit = pm.run([bell()])
        with Session(backend=backend) as session:
            sampler = SamplerV2(mode=session)
            job = sampler.run(isa_circuit)
            job.result()

        with mock.patch.object(service._get_api_client(), "create_session") as mock_create_session:
            new_session = Session.from_id(session_id=session._session_id, service=service)
            mock_create_session.assert_not_called()

        self.assertEqual(session._session_id, new_session._session_id)
        new_session.close()
        self.assertFalse(new_session._active)
        self.assertFalse(new_session.details()["accepting_jobs"])

        with self.assertRaises(IBMInputValueError):
            Batch.from_id(session_id=session._session_id, service=service)

    @run_integration_test
    def test_session_from_id_no_backend(self, service):
        """Test error is raised if session has no backend."""
        backend = service.backend(self.dependencies.qpu)
        if backend.configuration().simulator:
            raise SkipTest("No proper backends available")

        with Session(backend=backend) as session:
            _ = SamplerV2(mode=session)

        if session.details().get("backend_name") == "":
            with self.assertRaises(IBMRuntimeError):
                Session.from_id(session_id=session._session_id, service=service)

    @run_integration_test
    def test_session_backend(self, service):
        """Test session backend is the correct backend."""
        backend = service.backend(self.dependencies.qpu)

        pm = generate_preset_pass_manager(optimization_level=1, target=backend.target)
        instruction_name = "test_name"
        backend.target.add_instruction(IfElseOp, name=instruction_name)

        with Session(backend=backend) as session:
            sampler = SamplerV2(mode=session)
            job = sampler.run([pm.run(bell())])
            self.assertIn(instruction_name, job.backend().target.operation_names)

            sampler2 = SamplerV2()
            job2 = sampler2.run([pm.run(bell())])
            self.assertIn(instruction_name, job2.backend().target.operation_names)

    def test_session_instance_logic(self):
        """Test creating a session with different service configurations."""
        # test with no instances passed in
        service_no_instance = QiskitRuntimeService(
            token=self.dependencies.token,
            channel="ibm_quantum_platform",
            url=self.dependencies.url,
        )

        backend = service_no_instance.backend(self.dependencies.qpu)
        session = Session(backend=backend)
        self.assertTrue(session)
        session.close()

        # test when instance name is used at service init
        instance_name = _get_service_instance_name_for_crn(self.dependencies)
        service_with_instance_name = QiskitRuntimeService(
            token=self.dependencies.token,
            instance=instance_name,
            channel="ibm_quantum_platform",
            url=self.dependencies.url,
        )

        backend = service_with_instance_name.backend(self.dependencies.qpu)
        session = Session(backend=backend)
        self.assertTrue(session)
        session.close()
