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

from unittest import SkipTest, mock
from datetime import datetime, timedelta
import copy

from qiskit.transpiler.target import Target
from qiskit import QuantumCircuit
from qiskit.providers.exceptions import QiskitBackendNotFoundError
from qiskit.test.reference_circuits import ReferenceCircuits

from qiskit_ibm_provider.ibm_qubit_properties import IBMQubitProperties
from qiskit_ibm_provider.exceptions import IBMBackendValueError

from qiskit_ibm_runtime import QiskitRuntimeService

from ..ibm_test_case import IBMIntegrationTestCase
from ..decorators import run_integration_test, production_only, quantum_only


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
    @quantum_only
    def test_backends_no_config(self, service):
        """Test retrieving backends when a config is missing."""
        service._backend_configs = {}
        instance = service._account.instance
        backends = service.backends(instance=instance)
        configs = service._backend_configs
        configs["test_backend"] = None
        backend_names = [backend.name for backend in backends]
        # check filters still work
        service.backends(instance=instance, simulator=True)

        for config in configs.values():
            backend = service._create_backend_obj(config, instance=instance)
            if backend:
                self.assertTrue(backend.name in backend_names)

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

    @production_only
    def test_backend_target(self):
        """Check if the target property is set."""
        backend = self.backend
        with self.subTest(backend=backend.name):
            self.assertIsNotNone(backend.target)
            self.assertIsInstance(backend.target, Target)

    @production_only
    def test_backend_target_history(self):
        """Check retrieving backend target_history."""
        backend = self.backend
        with self.subTest(backend=backend.name):
            self.assertIsNotNone(backend.target_history())
            self.assertIsNotNone(backend.target_history(datetime=datetime.now() - timedelta(30)))

    def test_backend_max_circuits(self):
        """Check if the max_circuits property is set."""
        backend = self.backend
        with self.subTest(backend=backend.name):
            self.assertIsNotNone(backend.max_circuits)

    @production_only
    def test_backend_qubit_properties(self):
        """Check if the qubit properties are set."""
        backend = self.backend
        with self.subTest(backend=backend.name):
            if backend.simulator:
                raise SkipTest("Skip since simulator does not have qubit properties.")
            self.assertIsNotNone(backend.qubit_properties(0))

    @production_only
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

    @production_only
    def test_backend_properties(self):
        """Check the properties of calibration of a real chip."""
        backend = self.backend
        with self.subTest(backend=backend.name):
            if backend.simulator:
                raise SkipTest("Skip since simulator does not have properties.")
            properties = backend.properties()
            properties_today = backend.properties(datetime=datetime.today())
            self.assertIsNotNone(properties)
            self.assertIsNotNone(properties_today)
            self.assertEqual(properties.backend_version, properties_today.backend_version)

    @production_only
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

    @production_only
    def test_backend_invalid_attribute(self):
        """Check if AttributeError is raised when an invalid backend attribute is accessed."""
        backend = self.backend
        with self.subTest(backend=backend.name):
            with self.assertRaises(AttributeError):
                backend.foobar  # pylint: disable=pointless-statement

    def test_backend_deepcopy(self):
        """Test that deepcopy on IBMBackend works correctly"""
        backend = self.backend
        with self.subTest(backend=backend.name):
            backend_copy = copy.deepcopy(backend)
            self.assertEqual(backend_copy.name, backend.name)
            self.assertEqual(
                backend_copy.configuration().basis_gates,
                backend.configuration().basis_gates,
            )
            if backend.properties():
                self.assertEqual(
                    backend_copy.properties().last_update_date,
                    backend.properties().last_update_date,
                )
            self.assertEqual(backend_copy._instance, backend._instance)
            self.assertEqual(backend_copy._service._backends, backend._service._backends)
            self.assertEqual(backend_copy._get_defaults(), backend._get_defaults())
            self.assertEqual(
                backend_copy._api_client._session.base_url,
                backend._api_client._session.base_url,
            )

    def test_backend_pending_jobs(self):
        """Test pending jobs are returned."""
        if self.dependencies.channel == "ibm_cloud":
            raise SkipTest("Cloud account does not have real backend.")
        backends = self.service.backends()
        self.assertTrue(any(backend.status().pending_jobs > 0 for backend in backends))

    def test_backend_fetch_all_qubit_properties(self):
        """Check retrieving properties of all qubits"""
        if self.dependencies.channel == "ibm_cloud":
            raise SkipTest("Cloud channel does not have instance.")
        num_qubits = self.backend.num_qubits
        qubits = list(range(num_qubits))
        qubit_properties = self.backend.qubit_properties(qubits)
        self.assertEqual(len(qubit_properties), num_qubits)
        for i in qubits:
            self.assertIsInstance(qubit_properties[i], IBMQubitProperties)

    def test_sim_backend_options(self):
        """Test simulator backend options."""
        backend = self.service.backend("ibmq_qasm_simulator")
        backend.options.shots = 2048
        backend.set_options(memory=True)
        inputs = backend.run(ReferenceCircuits.bell(), shots=1, foo="foo").inputs
        self.assertEqual(inputs["shots"], 1)
        self.assertTrue(inputs["memory"])
        self.assertEqual(inputs["foo"], "foo")

    @production_only
    def test_paused_backend_warning(self):
        """Test that a warning is given when running jobs on a paused backend."""
        backend = self.service.backend("ibmq_qasm_simulator")
        paused_status = backend.status()
        paused_status.status_msg = "internal"
        backend.status = mock.MagicMock(return_value=paused_status)
        with self.assertWarns(Warning):
            backend.run(ReferenceCircuits.bell())

    def test_backend_wrong_instance(self):
        """Test that an error is raised when retrieving a backend not in the instance."""
        if self.dependencies.channel == "ibm_cloud":
            raise SkipTest("Cloud channel does not have instance.")

        backends = self.service.backends()
        hgps = self.service._hgps.values()
        if len(hgps) >= 2:
            for hgp in hgps:
                backend_names = list(hgp._backends)
                for backend in backends:
                    if backend.name not in backend_names:
                        with self.assertRaises(QiskitBackendNotFoundError):
                            self.service.backend(
                                backend.name,
                                instance=f"{hgp._hub}/{hgp._group}/{hgp._project}",
                            )
                        return

    def test_retrieve_backend_not_exist(self):
        """Test that an error is raised when retrieving a backend that does not exist."""
        with self.assertRaises(QiskitBackendNotFoundError):
            self.service.backend("nonexistent_backend")

    def test_too_many_qubits_in_circuit(self):
        """Check error message if circuit contains more qubits than supported on the backend."""
        if self.dependencies.channel == "ibm_cloud":
            raise SkipTest("Cloud channel does not have instance.")
        num = len(self.backend.properties().qubits)
        num_qubits = num + 1
        circuit = QuantumCircuit(num_qubits, num_qubits)
        with self.assertRaises(IBMBackendValueError) as err:
            _ = self.backend.run(circuit)
        self.assertIn(
            f"Circuit contains {num_qubits} qubits, but backend has only {num}.",
            str(err.exception),
        )
