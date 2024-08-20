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

from unittest import SkipTest

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

        backend = service.backend("ibmq_qasm_simulator")
        pass_mgr = generate_preset_pass_manager(backend=backend, optimization_level=1)
        psi1 = pass_mgr.run(RealAmplitudes(num_qubits=2, reps=2))
        # pylint: disable=invalid-name
        H1 = SparsePauliOp.from_list([("II", 1), ("IZ", 2), ("XI", 3)])
        theta1 = [0, 1, 1, 2, 3, 5]

        pm = generate_preset_pass_manager(optimization_level=1, target=backend.target)

        with Session(service, backend=backend) as session:
            estimator = EstimatorV2(session=session)
            result = estimator.run([(psi1, H1, [theta1])]).result()
            self.assertIsInstance(result, PrimitiveResult)

            sampler = SamplerV2(session=session)
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
        backend = service.backend("ibmq_qasm_simulator", instance=instance)
        pm = generate_preset_pass_manager(optimization_level=1, target=backend.target)
        with Session(service, backend=backend) as session:
            sampler = SamplerV2(session=session)
            job = sampler.run([pm.run(bell())])
            self.assertEqual(instance, backend._instance)
            self.assertEqual(instance, job.backend()._instance)

    @run_integration_test
    def test_session_from_id(self, service):
        """Test creating a session from a given id"""
        try:
            backend = service.backend("fake_backend1")
        except:
            raise SkipTest("No proper backends available")
        pm = generate_preset_pass_manager(backend=backend, optimization_level=1)
        isa_circuit = pm.run([bell()])
        with Session(service, backend=backend) as session:
            sampler = SamplerV2(session=session)
            sampler.run(isa_circuit)

        new_session = Session.from_id(session_id=session._session_id, service=service)
        self.assertEqual(session._session_id, new_session._session_id)
        self.assertTrue(new_session._active)
        new_session.close()
        self.assertFalse(new_session._active)

        with self.assertRaises(IBMInputValueError):
            Batch.from_id(session_id=session._session_id, service=service)

    @run_integration_test
    def test_job_mode_warning(self, service):
        """Test deprecation warning is raised when using job mode inside a session."""
        backend = service.backend("ibmq_qasm_simulator")
        with Session(service, backend=backend):
            with self.assertWarns(DeprecationWarning):
                _ = SamplerV2(mode=backend)
