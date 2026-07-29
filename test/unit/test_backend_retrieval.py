# This code is part of Qiskit.
#
# (C) Copyright IBM 2021-2026.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Backends Filtering Test."""

from unittest import mock

from ddt import ddt, named_data
from qiskit.providers.exceptions import QiskitBackendNotFoundError

from qiskit_ibm_runtime.accounts import Account
from qiskit_ibm_runtime.fake_provider import FakeFractionalBackend, FakeTorino
from qiskit_ibm_runtime.qiskit_runtime_service import QiskitRuntimeService

from ..decorators import mock_responses
from ..ibm_test_case import IBMTestCase
from ..registries import Backend, OneInstanceNoBackendsRegistry


class TestBackendFilters(IBMTestCase):
    """Qiskit Backend Filtering Tests."""

    @mock_responses
    def test_backend_instance_warnings(self, registry):
        """Test backend instance warnings."""
        service = QiskitRuntimeService(token="my_token")
        with self.assertLogs("qiskit_ibm_runtime", level="WARNING") as logs:
            service.backends()
        self.assertIn("Loading instance", logs.output[0])

        with self.assertLogs("qiskit_ibm_runtime", level="WARNING") as logs:
            service.backend("common_backend")
        self.assertIn("Using instance", logs.output[0])

    @mock_responses
    def test_instance_auto_suppresses_backends_loading_warning(self, registry):
        """instance='auto' must suppress 'Loading instance' warnings in backends()."""
        # Create service outside the log capture so init's "Loading account" doesn't interfere.
        service = QiskitRuntimeService(token="my_token", instance="auto")
        with self.assertNoLogs("qiskit_ibm_runtime", level="WARNING"):
            service.backends()

    @mock_responses
    def test_instance_auto_suppresses_backend_using_warning(self, registry):
        """instance='auto' must suppress 'Using instance' warning when looking up by name."""
        # Create service outside the log capture so init's "Loading account" doesn't interfere.
        service = QiskitRuntimeService(token="my_token", instance="auto")
        with self.assertNoLogs("qiskit_ibm_runtime", level="WARNING"):
            service.backend("common_backend")

    @mock_responses
    def test_saved_account_instance_auto_suppresses_warnings(self, registry):
        """A saved account with instance='auto' must suppress backend instance warnings."""
        saved_account = Account.create_account(
            channel="ibm_quantum_platform", token="my_token", instance="auto"
        )
        with mock.patch.object(
            QiskitRuntimeService, "_discover_account", return_value=saved_account
        ):
            service = QiskitRuntimeService(channel="ibm_quantum_platform", token="my_token")

        with self.assertNoLogs("qiskit_ibm_runtime", level="WARNING"):
            service.backends()
        with self.assertNoLogs("qiskit_ibm_runtime", level="WARNING"):
            service.backend("common_backend")

    @mock_responses
    def test_no_filter(self, registry):
        """Test no filtering."""
        service = QiskitRuntimeService(token="my_token")
        # QiskitRuntimeService with DefaultRegistry by default creates 3 backends.
        backend_name = [back.name for back in service.backends()]
        self.assertEqual(len(backend_name), 3)

    @mock_responses
    def test_filter_by_name(self, registry):
        """Test filtering by name."""
        service = QiskitRuntimeService(token="my_token")
        for name in [
            "common_backend",
            "unique_backend_a",
        ]:
            with self.subTest(name=name):
                backend_name = [back.name for back in service.backends(name=name)]
                self.assertEqual(len(backend_name), 1)

    @mock_responses(OneInstanceNoBackendsRegistry)
    def test_filter_config_properties(self, registry):
        """Test filtering by configuration properties."""
        n_qubits = 5
        backend_5q = Backend("5q")
        backend_5q.configuration.update({"n_qubits": 5, "local": False})
        backend_10q = Backend("10q")
        backend_10q.configuration.update({"n_qubits": 10, "local": False})
        backend_5q2 = Backend("5q2")
        backend_5q2.configuration.update({"n_qubits": 5, "local": True})
        registry.add_backend(backend_5q)
        registry.add_backend(backend_10q)
        registry.add_backend(backend_5q2)

        service = QiskitRuntimeService(token="my_token")
        filtered_backends = service.backends(n_qubits=n_qubits, local=False)
        self.assertTrue(len(filtered_backends), 1)
        self.assertEqual(n_qubits, filtered_backends[0].configuration().n_qubits)
        self.assertFalse(filtered_backends[0].configuration().local)

    @mock_responses(OneInstanceNoBackendsRegistry)
    def test_filter_status_dict(self, registry):
        """Test filtering by dictionary of mixed status/configuration properties."""
        backend_1 = Backend("backend_1")
        backend_1.configuration.update({"simulator": True})
        backend_2 = Backend("backend_2")
        backend_2.configuration.update({"simulator": True})
        backend_3 = Backend("backend_3")
        backend_3.configuration.update({"simulator": False})
        backend_4 = Backend("backend_4", status="offline")
        backend_4.configuration.update({"simulator": True})
        registry.add_backend(backend_1)
        registry.add_backend(backend_2)
        registry.add_backend(backend_3)
        registry.add_backend(backend_4)

        service = QiskitRuntimeService(token="my_token")
        filtered_backends = service.backends(
            operational=True,  # from status
            simulator=True,  # from configuration
        )
        self.assertTrue(len(filtered_backends), 2)
        for backend in filtered_backends:
            self.assertTrue(backend.status().operational)
            self.assertTrue(backend.configuration().simulator)

    @mock_responses(OneInstanceNoBackendsRegistry)
    def test_filter_config_callable(self, registry):
        """Test filtering by lambda function on configuration properties."""
        n_qubits = 5
        backend_5q = Backend("5q")
        backend_5q.configuration.update({"n_qubits": n_qubits})
        backend_10q = Backend("10q")
        backend_10q.configuration.update({"n_qubits": n_qubits * 2})
        backend_4q = Backend("4q")
        backend_4q.configuration.update({"n_qubits": n_qubits - 1})
        registry.add_backend(backend_5q)
        registry.add_backend(backend_10q)
        registry.add_backend(backend_4q)

        service = QiskitRuntimeService(token="my_token")
        filtered_backends = service.backends(filters=lambda x: (x.configuration().n_qubits >= 5))
        self.assertTrue(len(filtered_backends), 2)
        for backend in filtered_backends:
            self.assertGreaterEqual(backend.configuration().n_qubits, n_qubits)

    @mock_responses(OneInstanceNoBackendsRegistry)
    def test_least_busy_use_fractional_gates_skips_backend_without_rzz(self, registry):
        """When use_fractional_gates=True, least_busy skips backends missing rzz."""
        registry.add_backend(Backend.from_(FakeTorino, queue_length=5))
        registry.add_backend(Backend.from_(FakeFractionalBackend, queue_length=10))

        service = QiskitRuntimeService(token="my_token")
        backend = service.least_busy(use_fractional_gates=True)
        self.assertEqual(backend.name, "fake_fractional")
        self.assertIn("rzz", backend.basis_gates)

    @mock_responses
    def test_least_busy_use_fractional_gates_no_qualifying_backend(self, registry):
        """When use_fractional_gates=True and no backend has rzz, raise an error."""
        service = QiskitRuntimeService(token="my_token")
        with self.assertRaises(QiskitBackendNotFoundError):
            service.least_busy(use_fractional_gates=True)

    @mock_responses(OneInstanceNoBackendsRegistry)
    def test_least_busy_use_fractional_gates_false_ignores_rzz(self, registry):
        """When use_fractional_gates=False (default), least_busy returns the least busy backend."""
        registry.add_backend(Backend.from_(FakeTorino, queue_length=5))
        registry.add_backend(Backend.from_(FakeFractionalBackend, queue_length=10))

        service = QiskitRuntimeService(token="token")
        backend = service.least_busy(use_fractional_gates=False)
        self.assertEqual(backend.name, "ibm_torino")

    @mock_responses(OneInstanceNoBackendsRegistry)
    def test_filter_least_busy(self, registry):
        """Test filtering by least busy function."""
        registry.add_backend(Backend("backend1", queue_length=10))
        registry.add_backend(Backend("backend2", queue_length=20))
        registry.add_backend(Backend("backend3", queue_length=1, status="offline"))
        registry.add_backend(Backend("backend4", queue_length=15))

        service = QiskitRuntimeService(token="my_token")
        backend = service.least_busy()
        self.assertEqual(backend.name, "backend1")

    @mock_responses(OneInstanceNoBackendsRegistry)
    def test_filter_min_num_qubits(self, registry):
        """Test filtering by minimum number of qubits."""
        n_qubits = 5
        backend_5q = Backend("5q")
        backend_5q.configuration.update({"n_qubits": n_qubits})
        backend_10q = Backend("10q")
        backend_10q.configuration.update({"n_qubits": n_qubits * 2})
        backend_4q = Backend("4q")
        backend_4q.configuration.update({"n_qubits": n_qubits - 1})
        registry.add_backend(backend_5q)
        registry.add_backend(backend_10q)
        registry.add_backend(backend_4q)

        service = QiskitRuntimeService(token="my_token")
        filtered_backends = service.backends(min_num_qubits=n_qubits)
        self.assertTrue(len(filtered_backends), 2)
        for backend in filtered_backends:
            self.assertGreaterEqual(backend.configuration().n_qubits, n_qubits)


@ddt
class TestGetBackend(IBMTestCase):
    """Test getting a backend."""

    @mock_responses(OneInstanceNoBackendsRegistry)
    def test_get_backend_properties(self, registry):
        """Test that a backend's properties are loaded into its target."""
        registry.add_backend(Backend.from_(FakeTorino))

        service = QiskitRuntimeService(token="my_token")
        backend = service.backend("ibm_torino")

        t1s = sorted(p.t1 for p in backend.target.qubit_properties)
        sx_errors = sorted(backend.target["sx"][q].error for q in backend.target["sx"])
        cz_errors = sorted(backend.target["cz"][p].error for p in backend.target["cz"])

        # Check right number of gates/properties loaded
        self.assertEqual(len(t1s), backend.num_qubits)
        self.assertEqual(len(sx_errors), backend.num_qubits)
        self.assertEqual(len(cz_errors), 300)
        # Check that the right property values were loaded
        self.assertAlmostEqual(t1s[0], 3.163e-6, places=8)
        self.assertAlmostEqual(t1s[-1], 3.077e-4, places=6)
        self.assertAlmostEqual(sx_errors[0], 1.1358e-4, places=7)
        self.assertAlmostEqual(sx_errors[-1], 0.01738, places=5)
        self.assertAlmostEqual(cz_errors[0], 0.001495, places=5)
        self.assertAlmostEqual(cz_errors[-1], 1.0, places=5)

    @named_data(
        ("with_fractional", True),
        ("without_fractional", False),
        ("without_filtering", None),
    )
    @mock_responses(OneInstanceNoBackendsRegistry)
    def test_get_backend_with_fractional_optin(self, use_fractional, registry):
        """Test getting backend with fractional gate opt-in.

        This test can be modified when the IBM backend architecture changes in future.
        In our backend as of today, fractional gates and dynamic circuits are
        only exclusively supported.

        This test is originally written in 2024.05.31
        """
        registry.add_backend(Backend.from_(FakeFractionalBackend, queue_length=10))
        service = QiskitRuntimeService(token="my_token")

        test_backend = service.backends("fake_fractional", use_fractional_gates=use_fractional)[0]
        self.assertEqual(
            "rx" in test_backend.target,
            use_fractional or use_fractional is None,
        )
        self.assertEqual(
            "rzz" in test_backend.target,
            use_fractional or use_fractional is None,
        )
        self.assertTrue("if_else" in test_backend.target.operation_names)
        self.assertTrue("while_loop" in test_backend.target.operation_names)

        if use_fractional or use_fractional is None:
            self.assertAlmostEqual(test_backend.target["rx"][(0,)].error, 0.00019, places=5)

    @mock_responses(OneInstanceNoBackendsRegistry)
    def test_backend_with_and_without_fractional_from_same_service(self, registry):
        """Test getting backend with and without fractional gates from the same service.

        Backend with and without opt-in must be different object.
        """
        registry.add_backend(Backend.from_(FakeFractionalBackend, queue_length=10))
        service = QiskitRuntimeService(token="my_token")

        backend_with_fg = service.backend("fake_fractional", use_fractional_gates=True)
        self.assertIn("rx", backend_with_fg.target)

        backend_without_fg = service.backend("fake_fractional", use_fractional_gates=False)
        self.assertNotIn("rx", backend_without_fg.target)
        self.assertIn("rx", backend_with_fg.target)

        self.assertIsNot(backend_with_fg, backend_without_fg)

    @mock_responses(OneInstanceNoBackendsRegistry, expose_responses_mock=True)
    def test_backend_with_custom_calibration(self, registry, requests_mock):
        """Test getting a backend with a custom calibration."""
        registry.add_backend(Backend.from_(FakeTorino, queue_length=5))
        service = QiskitRuntimeService(token="my_token")

        backend_with_calibration = service.backend("ibm_torino", calibration_id="abc1234")
        self.assertEqual(backend_with_calibration.calibration_id, "abc1234")
        # Assert mock has api client calls with cal id set
        self.assertIn("calibration_id=abc1234", requests_mock.calls[-1].request.url)
