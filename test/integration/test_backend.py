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

from unittest import mock
from datetime import datetime, timedelta
import copy

from qiskit.transpiler.target import Target
from qiskit import QuantumCircuit, transpile
from qiskit.providers.exceptions import QiskitBackendNotFoundError
from qiskit.providers.backend import QubitProperties
from qiskit_ibm_runtime.exceptions import IBMInputValueError

from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2 as Sampler

from ..ibm_test_case import IBMIntegrationTestCase
from ..decorators import run_integration_test, production_only
from ..utils import bell


class TestIntegrationBackend(IBMIntegrationTestCase):
    """Integration tests for backend functions."""

    @run_integration_test
    def test_least_busy(self, service):
        """Test the least busy method."""
        # test passing an instance
        instance = self.dependencies.instance
        backend = service.least_busy(instance=instance)
        self.assertEqual(instance, backend._instance)

        # test when there is no instance
        service_with_no_default_instance = QiskitRuntimeService(
            token=self.dependencies.token,
            channel="ibm_quantum_platform",
            url=self.dependencies.url,
        )
        backend = service_with_no_default_instance.least_busy()
        self.assertTrue(backend)

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

    @run_integration_test
    def test_target_reset(self, service):
        """Test confirming target contains reset."""
        backend = service.backend(self.dependencies.qpu)
        self.assertIn("reset", backend.target)


class TestIBMBackend(IBMIntegrationTestCase):
    """Test ibm_backend module."""

    @classmethod
    def setUpClass(cls):
        """Initial class level setup."""
        # pylint: disable=arguments-differ
        # pylint: disable=no-value-for-parameter
        super().setUpClass()
        if cls.dependencies.channel == "ibm_quantum_platform":
            cls.backend = cls.dependencies.service.backend(cls.dependencies.qpu)

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

    @production_only
    def test_properties_not_cached_target_history(self):
        """Check backend properties is not cached in target_history()."""
        backend = self.backend
        with self.subTest(backend=backend.name):
            properties = backend.properties()
            backend.target_history(datetime=datetime.now() - timedelta(60))
            self.assertEqual(properties, backend.properties())

    def test_backend_target_refresh(self):
        """Test refreshing the backend target."""
        backend = self.backend
        with self.subTest(backend=backend.name):
            old_target = backend.target
            old_configuration = backend.configuration()
            old_properties = backend.properties()
            backend.refresh()
            new_target = backend.target
            self.assertNotEqual(old_target, new_target)
            self.assertIsNot(old_configuration, backend.configuration())
            self.assertIsNot(old_properties, backend.properties())

    def test_backend_qubit_properties(self):
        """Check if the qubit properties are set."""
        backend = self.backend
        with self.subTest(backend=backend.name):
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
            properties = backend.properties()
            properties_today = backend.properties(datetime=datetime.today())
            self.assertIsNotNone(properties)
            self.assertIsNotNone(properties_today)
            self.assertEqual(properties.backend_version, properties_today.backend_version)

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
            self.assertEqual(
                backend_copy._api_client._session.base_url,
                backend._api_client._session.base_url,
            )

    def test_backend_pending_jobs(self):
        """Test pending jobs are returned."""
        backends = self.service.backends()
        self.assertTrue(any(backend.status().pending_jobs >= 0 for backend in backends))

    def test_backend_fetch_all_qubit_properties(self):
        """Check retrieving properties of all qubits"""
        num_qubits = self.backend.num_qubits
        qubits = list(range(num_qubits))
        qubit_properties = self.backend.qubit_properties(qubits)
        self.assertEqual(len(qubit_properties), num_qubits)
        for i in qubits:
            self.assertIsInstance(qubit_properties[i], QubitProperties)

    def test_sim_backend_options(self):
        """Test simulator backend options."""
        backend = self.backend
        backend.options.shots = 2048
        backend.set_options(memory=True)
        sampler = Sampler(mode=backend)
        isa_circuit = transpile(bell(), backend)
        inputs = sampler.run([isa_circuit], shots=1).inputs
        self.assertEqual(inputs["pubs"][0][2], 1)

    @production_only
    def test_paused_backend_warning(self):
        """Test that a warning is given when running jobs on a paused backend."""
        backend = self.backend
        paused_status = backend.status()
        paused_status.status_msg = "internal"
        backend.status = mock.MagicMock(return_value=paused_status)
        isa_circuit = transpile(bell(), backend)
        with self.assertWarns(Warning):
            sampler = Sampler(mode=backend)
            sampler.run([isa_circuit])

    def test_retrieve_backend_not_exist(self):
        """Test that an error is raised when retrieving a backend that does not exist."""
        with self.assertRaises(QiskitBackendNotFoundError):
            self.service.backend("nonexistent_backend")

    def test_too_many_qubits_in_circuit(self):
        """Check error message if circuit contains more qubits than supported on the backend."""
        num = len(self.backend.properties().qubits)
        num_qubits = num + 1
        circuit = QuantumCircuit(num_qubits, num_qubits)
        with self.assertRaises(IBMInputValueError) as err:
            sampler = Sampler(mode=self.backend)
            job = sampler.run([circuit])
            job.cancel()
        self.assertIn(
            f"circuit has {num_qubits} qubits but the target system requires {num}",
            str(err.exception),
        )

    def test_use_fractional_gates_flag(self):
        """Test use_fractional_gates returns correct backend config."""
        try:
            real_device_name = "alt_fez"
            real_device_no_fg = self.service.backend(real_device_name, use_fractional_gates=False)
            real_device_fg = self.service.backend(real_device_name, use_fractional_gates=True)
        except QiskitBackendNotFoundError:
            self.skipTest("Real backend not available.")
        self.assertIn("rzz", real_device_fg.basis_gates)
        self.assertNotIn("rzz", real_device_no_fg.basis_gates)

    def test_backend_fractional_gates_error(self):
        """Test that use_fractional_gates = True raises error for unsupported backends"""
        backend = self.backend
        with self.subTest(backend=backend.name):
            if "rzz" in backend.basis_gates:
                self.skipTest(f"Backend {backend.name} supports fractional gates, no error.")
            with self.assertRaises(
                IBMInputValueError,
                msg=(
                    f"Backend '{backend.name}' does not support fractional gates, "
                    "but use_fractional_gates was set to True."
                ),
            ):
                self.service.backend(backend.name, use_fractional_gates=True)

    def test_renew_backend_properties(self):
        """Test renewed backend property"""
        name = self.backend.name
        backend = self.service.backend(name)
        basis_gates = copy.copy(backend.basis_gates)
        # modify a property
        backend.basis_gates.remove(basis_gates[0])
        # renew backend
        backend = self.service.backend(name)
        self.assertEqual(backend.basis_gates, basis_gates)

    def test_backend_calibration_id(self):
        """Test calibration_id is used when fetching the configuration."""
        name = self.backend.name
        calibration_id = "invalid_id"
        with self.assertLogs("qiskit_ibm_runtime", level="WARNING") as log:
            with self.assertRaises(QiskitBackendNotFoundError):
                self.service.backend(name, calibration_id=calibration_id)

        self.assertTrue(any(calibration_id in record for record in log.output))
