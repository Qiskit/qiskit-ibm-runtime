# This code is part of Qiskit.
#
# (C) Copyright IBM 2021.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Tests for backend functions using real runtime service."""

import os
from unittest import SkipTest

from qiskit.transpiler.target import Target
from qiskit.providers.jobstatus import JobStatus
from qiskit.test.reference_circuits import ReferenceCircuits

from qiskit_ibm_runtime import QiskitRuntimeService

from ..ibm_test_case import IBMIntegrationTestCase
from ..decorators import run_integration_test


class TestIntegrationBackend(IBMIntegrationTestCase):
    """Integration tests for backend functions."""

    @run_integration_test
    def test_backends(self, service):
        """Test getting all backends."""
        backends = service.backends()
        self.assertTrue(backends)
        backend_names = [back.name for back in backends]
        self.assertEqual(
            len(backend_names),
            len(set(backend_names)),
            f"backend_names={backend_names}",
        )

    @run_integration_test
    def test_get_backend(self, service):
        """Test getting a backend."""
        backends = service.backends()
        backend = service.backend(backends[0].name)
        self.assertTrue(backend)


class TestIBMBackend(IBMIntegrationTestCase):
    """Test ibm_backend module."""

    @classmethod
    def setUpClass(cls):
        """Initial class level setup."""
        # pylint: disable=arguments-differ
        # pylint: disable=no-value-for-parameter
        super().setUpClass()
        if cls.dependencies.channel == "ibm_cloud":
            # TODO use real device when cloud supports it
            cls.backend = cls.dependencies.service.least_busy(min_num_qubits=5)
        if cls.dependencies.channel == "ibm_quantum":
            cls.backend = cls.dependencies.service.least_busy(
                simulator=False, min_num_qubits=5, instance=cls.dependencies.instance
            )

    def test_backend_service(self):
        """Check if the service property is set."""
        backend = self.backend
        with self.subTest(backend=backend.name):
            self.assertIsInstance(backend.service, QiskitRuntimeService)

    def test_backend_target(self):
        """Check if the target property is set."""
        backend = self.backend
        with self.subTest(backend=backend.name):
            self.assertIsNotNone(backend.target)
            self.assertIsInstance(backend.target, Target)

    def test_backend_max_circuits(self):
        """Check if the max_circuits property is set."""
        backend = self.backend
        with self.subTest(backend=backend.name):
            self.assertIsNotNone(backend.max_circuits)

    def test_backend_qubit_properties(self):
        """Check if the qubit properties are set."""
        backend = self.backend
        with self.subTest(backend=backend.name):
            if backend.simulator:
                raise SkipTest("Skip since simulator does not have qubit properties.")
            self.assertIsNotNone(backend.qubit_properties(0))

    def test_backend_simulator(self):
        """Test if a configuration attribute (ex: simulator) is available as backend attribute."""
        backend = self.backend
        with self.subTest(backend=backend.name):
            self.assertIsNotNone(backend.simulator)
            self.assertEqual(backend.simulator, backend.configuration().simulator)

    def test_backend_status(self):
        """Check the status of a real chip."""
        backend = self.backend
        with self.subTest(backend=backend.name):
            self.assertTrue(backend.status().operational)

    def test_backend_properties(self):
        """Check the properties of calibration of a real chip."""
        backend = self.backend
        with self.subTest(backend=backend.name):
            if backend.simulator:
                raise SkipTest("Skip since simulator does not have properties.")
            self.assertIsNotNone(backend.properties())

    def test_backend_pulse_defaults(self):
        """Check the backend pulse defaults of each backend."""
        backend = self.backend
        with self.subTest(backend=backend.name):
            if backend.simulator:
                raise SkipTest("Skip since simulator does not have defaults.")
            if not backend.open_pulse:
                raise SkipTest("Skip for backends that do not support pulses.")
            self.assertIsNotNone(backend.defaults())

    def test_backend_configuration(self):
        """Check the backend configuration of each backend."""
        backend = self.backend
        with self.subTest(backend=backend.name):
            self.assertIsNotNone(backend.configuration())

    def test_backend_invalid_attribute(self):
        """Check if AttributeError is raised when an invalid backend attribute is accessed."""
        backend = self.backend
        with self.subTest(backend=backend.name):
            with self.assertRaises(AttributeError):
                backend.foobar  # pylint: disable=pointless-statement

    def test_backend_run(self):
        """Test running a job from a backend."""
        if self.dependencies.channel == "ibm_cloud":
            raise SkipTest(
                "Skip since cloud account does not have circuit-runner program."
            )
        if os.environ.get("QISKIT_IBM_USE_STAGING_CREDENTIALS", ""):
            backend = self.dependencies.service.backend("ibmq_qasm_simulator")
            job = backend.run(ReferenceCircuits.bell(), shots=10)
        else:
            job = self.backend.run(ReferenceCircuits.bell(), shots=10)
        job.wait_for_final_state()
        result = job.result()
        self.assertTrue(result)
        self.assertEqual(result["results"][0]["shots"], 10)
        self.assertEqual(JobStatus.DONE, job.status())
