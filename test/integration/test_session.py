# This code is part of Qiskit.
#
# (C) Copyright IBM 2022-2026.
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

from qiskit.circuit import IfElseOp
from qiskit.circuit.library import real_amplitudes
from qiskit.primitives import PrimitiveResult
from qiskit.quantum_info import SparsePauliOp
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

from qiskit_ibm_runtime import Batch, EstimatorV2, QiskitRuntimeService, SamplerV2, Session
from qiskit_ibm_runtime.exceptions import IBMInputValueError, IBMRuntimeError

from ..utils import bell
from .case import IBMIntegrationTestCase
from .test_account import _get_service_instance_name_for_crn


class TestIntegrationSession(IBMIntegrationTestCase):
    """Integration tests for Session."""

    def test_estimator_sampler(self):
        """Test calling both estimator and sampler."""
        service = self.service
        backend = service.backend(self.dependencies.qpu)

        pm = generate_preset_pass_manager(optimization_level=1, target=backend.target)
        psi1 = pm.run(real_amplitudes(num_qubits=2, reps=2))

        H1 = SparsePauliOp.from_list([("II", 1), ("IZ", 2), ("XI", 3)]).apply_layout(psi1.layout)
        theta1 = [0, 1, 1, 2, 3, 5]

        with Session(backend=backend) as session:
            estimator = EstimatorV2(mode=session)
            result = estimator.run([(psi1, H1, [theta1])]).result()
            assert isinstance(result, PrimitiveResult)

            sampler = SamplerV2(mode=session)
            result = sampler.run([pm.run(bell())]).result()
            assert isinstance(result, PrimitiveResult)

            result = estimator.run([(psi1, H1, [theta1])]).result()
            assert isinstance(result, PrimitiveResult)
            assert result[0].metadata["shots"] == 4096

            result = sampler.run([pm.run(bell())]).result()
            assert isinstance(result, PrimitiveResult)
            session.close()

    def test_session_from_id(self):
        """Test creating a session from a given id."""
        service = self.service
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

        assert session._session_id == new_session._session_id
        new_session.close()
        assert not new_session._active
        assert not new_session.details()["accepting_jobs"]

        with self.assertRaises(IBMInputValueError):
            Batch.from_id(session_id=session._session_id, service=service)

    def test_session_from_id_no_backend(self):
        """Test error is raised if session has no backend."""
        service = self.service
        backend = service.backend(self.dependencies.qpu)
        if backend.configuration().simulator:
            raise SkipTest("No proper backends available")

        with Session(backend=backend) as session:
            _ = SamplerV2(mode=session)

        if session.details().get("backend_name") == "":
            with self.assertRaises(IBMRuntimeError):
                Session.from_id(session_id=session._session_id, service=service)

    def test_session_backend(self):
        """Test session backend is the correct backend."""
        service = self.service
        backend = service.backend(self.dependencies.qpu)

        pm = generate_preset_pass_manager(optimization_level=1, target=backend.target)
        instruction_name = "test_name"
        backend.target.add_instruction(IfElseOp, name=instruction_name)

        with Session(backend=backend) as session:
            sampler = SamplerV2(mode=session)
            job = sampler.run([pm.run(bell())])
            assert instruction_name in job.backend().target.operation_names

            sampler2 = SamplerV2()
            job2 = sampler2.run([pm.run(bell())])
            assert instruction_name in job2.backend().target.operation_names

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
        assert session
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
        assert session
        session.close()
