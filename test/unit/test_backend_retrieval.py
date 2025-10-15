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

"""Backends Filtering Test."""

import uuid
from ddt import ddt, named_data

from qiskit_ibm_runtime.fake_provider import FakeLimaV2

from .mock.fake_runtime_service import FakeRuntimeService
from .mock.fake_api_backend import FakeApiBackendSpecs
from ..ibm_test_case import IBMTestCase
from ..decorators import run_cloud_fake


class TestBackendFilters(IBMTestCase):
    """Qiskit Backend Filtering Tests."""

    @run_cloud_fake
    def test_backend_instance_warnings(self, service):
        """Test backend instance warnings"""
        with self.assertLogs("qiskit_ibm_runtime", level="WARNING") as logs:
            service.backends()
        self.assertIn("Loading instance", logs.output[0])

        with self.assertLogs("qiskit_ibm_runtime", level="WARNING") as logs:
            service.backend("common_backend")
        self.assertIn("Using instance", logs.output[0])

    @run_cloud_fake
    def test_no_filter(self, service):
        """Test no filtering."""
        # FakeRuntimeService by default creates 3 backends.
        backend_name = [back.name for back in service.backends()]
        self.assertEqual(len(backend_name), 3)

    @run_cloud_fake
    def test_filter_by_name(self, service):
        """Test filtering by name."""
        for name in [
            FakeRuntimeService.DEFAULT_COMMON_BACKEND,
            FakeRuntimeService.DEFAULT_UNIQUE_BACKEND_PREFIX + "0",
        ]:
            with self.subTest(name=name):
                backend_name = [back.name for back in service.backends(name=name)]
                self.assertEqual(len(backend_name), 1)

    def test_filter_config_properties(self):
        """Test filtering by configuration properties."""
        n_qubits = 5
        fake_backends = [
            self._get_fake_backend_specs(n_qubits=n_qubits, local=False),
            self._get_fake_backend_specs(n_qubits=n_qubits * 2, local=False),
            self._get_fake_backend_specs(n_qubits=n_qubits, local=True),
        ]

        services = self._get_services(fake_backends)
        for service in services:
            with self.subTest(service=service.channel):
                filtered_backends = service.backends(n_qubits=n_qubits, local=False)
                self.assertTrue(len(filtered_backends), 1)
                self.assertEqual(n_qubits, filtered_backends[0].configuration().n_qubits)
                self.assertFalse(filtered_backends[0].configuration().local)

    def test_filter_status_dict(self):
        """Test filtering by dictionary of mixed status/configuration properties."""
        fake_backends = [
            self._get_fake_backend_specs(operational=True, simulator=True),
            self._get_fake_backend_specs(operational=True, simulator=True),
            self._get_fake_backend_specs(operational=True, simulator=False),
            self._get_fake_backend_specs(operational=False, simulator=False),
        ]

        services = self._get_services(fake_backends)
        for service in services:
            with self.subTest(service=service.channel):
                filtered_backends = service.backends(
                    operational=True,  # from status
                    simulator=True,  # from configuration
                )
                self.assertTrue(len(filtered_backends), 2)
                for backend in filtered_backends:
                    self.assertTrue(backend.status().operational)
                    self.assertTrue(backend.configuration().simulator)

    def test_filter_config_callable(self):
        """Test filtering by lambda function on configuration properties."""
        n_qubits = 5
        fake_backends = [
            self._get_fake_backend_specs(n_qubits=n_qubits),
            self._get_fake_backend_specs(n_qubits=n_qubits * 2),
            self._get_fake_backend_specs(n_qubits=n_qubits - 1),
        ]

        services = self._get_services(fake_backends)
        for service in services:
            with self.subTest(service=service.channel):
                filtered_backends = service.backends(
                    filters=lambda x: (x.configuration().n_qubits >= 5)
                )
                self.assertTrue(len(filtered_backends), 2)
                for backend in filtered_backends:
                    self.assertGreaterEqual(backend.configuration().n_qubits, n_qubits)

    def test_filter_least_busy(self):
        """Test filtering by least busy function."""
        default_stat = {"pending_jobs": 1, "operational": True, "status_msg": "active"}
        backends_list = [
            {
                "name": "test_backend1",
                "status": {"name": "online", "reason": "Available"},
                "queue_length": 10,
            },
            {
                "name": "test_backend2",
                "status": {"name": "online"},
                "queue_length": 20,
            },
            {
                "name": "test_backend3",
                "status": {"name": "offline", "reason": "available"},
                "queue_length": 1,
            },
            {
                "name": "test_backend4",
                "status": {"name": "online", "reason": "available"},
                "queue_length": 15,
            },
        ]
        fake_backends = [
            self._get_fake_backend_specs(**{**default_stat, "backend_name": "test_backend1"}),
            self._get_fake_backend_specs(**{**default_stat, "backend_name": "test_backend2"}),
            self._get_fake_backend_specs(**{**default_stat, "backend_name": "test_backend3"}),
            self._get_fake_backend_specs(**{**default_stat, "backend_name": "test_backend4"}),
        ]

        services = self._get_services(fake_backends)
        for service in services:
            with self.subTest(service=service.channel):
                service._backends_list = backends_list
                backend = service.least_busy()
                self.assertEqual(backend.name, "test_backend1")

    def test_filter_min_num_qubits(self):
        """Test filtering by minimum number of qubits."""
        n_qubits = 5
        fake_backends = [
            self._get_fake_backend_specs(n_qubits=n_qubits),
            self._get_fake_backend_specs(n_qubits=n_qubits * 2),
            self._get_fake_backend_specs(n_qubits=n_qubits - 1),
        ]

        services = self._get_services(fake_backends)
        for service in services:
            with self.subTest(service=service.channel):
                filtered_backends = service.backends(min_num_qubits=n_qubits)
                self.assertTrue(len(filtered_backends), 2)
                for backend in filtered_backends:
                    self.assertGreaterEqual(backend.configuration().n_qubits, n_qubits)

    def _get_fake_backend_specs(self, crns=None, **kwargs):
        """Get the backend specs to pass to the fake client."""
        config = {}
        status = {}
        status_keys = FakeLimaV2().status().to_dict()
        status_keys.pop("backend_name")  # name is in both config and status
        status_keys = list(status_keys.keys())
        for key, val in kwargs.items():
            if key in status_keys:
                status[key] = val
            else:
                config[key] = val
        name = config.get("backend_name", uuid.uuid4().hex)
        return FakeApiBackendSpecs(
            backend_name=name, configuration=config, status=status, crns=crns
        )

    def _get_services(self, fake_backend_specs):
        """Get ibm_cloud services initialized with fake backends."""
        cloud_service = FakeRuntimeService(
            channel="ibm_cloud",
            token="my_token",
            instance="crn:v1:bluemix:public:quantum-computing:my-region:a/...:...::",
            backend_specs=fake_backend_specs,
        )
        return [cloud_service]


@ddt
class TestGetBackend(IBMTestCase):
    """Test getting a backend."""

    def test_get_backend_properties(self):
        """Test that a backend's properties are loaded into its target"""
        service = FakeRuntimeService(
            channel="ibm_quantum_platform",
            token="my_token",
            backend_specs=[FakeApiBackendSpecs(backend_name="FakeTorino")],
        )
        backend = service.backend("fake_torino")

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
    def test_get_backend_with_fractional_optin(self, use_fractional):
        """Test getting backend with fractional gate opt-in.

        This test can be modified when the IBM backend architecture changes in future.
        In our backend as of today, fractional gates and dynamic circuits are
        only exclusively supported.

        This test is originally written in 2024.05.31
        """
        service = FakeRuntimeService(
            channel="ibm_quantum_platform",
            token="my_token",
            backend_specs=[FakeApiBackendSpecs(backend_name="FakeFractionalBackend")],
        )
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

    def test_backend_with_and_without_fractional_from_same_service(self):
        """Test getting backend with and without fractional gates from the same service.

        Backend with and without opt-in must be different object.
        """
        service = FakeRuntimeService(
            channel="ibm_quantum_platform",
            token="my_token",
            backend_specs=[FakeApiBackendSpecs(backend_name="FakeFractionalBackend")],
        )

        backend_with_fg = service.backend("fake_fractional", use_fractional_gates=True)
        self.assertIn("rx", backend_with_fg.target)

        backend_without_fg = service.backend("fake_fractional", use_fractional_gates=False)
        self.assertNotIn("rx", backend_without_fg.target)
        self.assertIn("rx", backend_with_fg.target)

        self.assertIsNot(backend_with_fg, backend_without_fg)

    def test_backend_with_custom_calibration(self):
        """Test getting a backend with a custom calibration."""
        service = FakeRuntimeService(
            channel="ibm_quantum_platform",
            token="my_token",
            backend_specs=[FakeApiBackendSpecs(backend_name="FakeTorino")],
        )

        backend_with_calibration = service.backend("fake_torino", calibration_id="abc1234")
        self.assertEqual(backend_with_calibration.calibration_id, "abc1234")
        # TODO: Assert mock has api client calls with cal id set
