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

from qiskit.providers.exceptions import QiskitBackendNotFoundError
from qiskit_ibm_runtime.fake_provider import FakeLima

from .mock.fake_runtime_service import FakeRuntimeService
from .mock.fake_api_backend import FakeApiBackendSpecs
from ..ibm_test_case import IBMTestCase
from ..decorators import run_quantum_and_cloud_fake


class TestBackendFilters(IBMTestCase):
    """Qiskit Backend Filtering Tests."""

    @run_quantum_and_cloud_fake
    def test_no_filter(self, service):
        """Test no filtering."""
        # FakeRuntimeService by default creates 3 backends.
        backend_name = [back.name for back in service.backends()]
        self.assertEqual(len(backend_name), 3)

    @run_quantum_and_cloud_fake
    def test_filter_by_name(self, service):
        """Test filtering by name."""
        for name in [
            FakeRuntimeService.DEFAULT_COMMON_BACKEND,
            FakeRuntimeService.DEFAULT_UNIQUE_BACKEND_PREFIX + "0",
        ]:
            with self.subTest(name=name):
                backend_name = [back.name for back in service.backends(name=name)]
                self.assertEqual(len(backend_name), 1)

    def test_filter_by_instance_ibm_quantum(self):
        """Test filtering by instance (works only on ibm_quantum)."""
        service = FakeRuntimeService(channel="ibm_quantum", token="my_token")
        for hgp in FakeRuntimeService.DEFAULT_HGPS:
            with self.subTest(hgp=hgp):
                backends = service.backends(instance=hgp)
                backend_name = [back.name for back in backends]
                self.assertEqual(len(backend_name), 2)
                for back in backends:
                    self.assertEqual(back._instance, hgp)

    def test_filter_by_service_instance_ibm_quantum(self):
        """Test filtering by QiskitRuntimeService._account.instance (works only on ibm_quantum)."""
        for hgp in FakeRuntimeService.DEFAULT_HGPS:
            service = FakeRuntimeService(channel="ibm_quantum", token="my_token", instance=hgp)
            with self.subTest(hgp=hgp):
                backends = service.backends()
                backend_name = [back.name for back in backends]
                self.assertEqual(len(backend_name), 2)
                for back in backends:
                    self.assertEqual(back._instance, hgp)

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
        fake_backends = [
            self._get_fake_backend_specs(
                **{**default_stat, "backend_name": "bingo", "pending_jobs": 5}
            ),
            self._get_fake_backend_specs(**{**default_stat, "pending_jobs": 7}),
            self._get_fake_backend_specs(**{**default_stat, "operational": False}),
            self._get_fake_backend_specs(**{**default_stat, "status_msg": "internal"}),
        ]

        services = self._get_services(fake_backends)
        for service in services:
            with self.subTest(service=service.channel):
                backend = service.least_busy()
                self.assertEqual(backend.name, "bingo")

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

    def test_filter_by_hgp(self):
        """Test filtering by hub/group/project."""
        num_backends = 3
        hgp_name = "hub0/group0/project0"
        hgp_backend_specs = [
            self._get_fake_backend_specs(hgps=[hgp_name]) for _ in range(num_backends)
        ]
        all_backend_specs = hgp_backend_specs + [
            self._get_fake_backend_specs(hgps=["hub1/group1/project1"])
        ]
        ibm_quantum_service = FakeRuntimeService(
            channel="ibm_quantum",
            token="my_token",
            instance="h/g/p",
            num_hgps=2,
            backend_specs=all_backend_specs,
        )
        backends = ibm_quantum_service.backends(instance="hub0/group0/project0")
        self.assertEqual(len(backends), num_backends)
        right_names = {spec.backend_name for spec in hgp_backend_specs}
        got_names = {back.name for back in backends}
        self.assertEqual(right_names, got_names)

    def _get_fake_backend_specs(self, hgps=None, **kwargs):
        """Get the backend specs to pass to the fake client."""
        config = {}
        status = {}
        status_keys = FakeLima().status().to_dict()
        status_keys.pop("backend_name")  # name is in both config and status
        status_keys = list(status_keys.keys())
        for key, val in kwargs.items():
            if key in status_keys:
                status[key] = val
            else:
                config[key] = val
        name = config.get("backend_name", uuid.uuid4().hex)
        return FakeApiBackendSpecs(
            backend_name=name, configuration=config, status=status, hgps=hgps
        )

    def _get_services(self, fake_backend_specs):
        """Get both ibm_cloud and ibm_quantum services initialized with fake backends."""
        ibm_quantum_service = FakeRuntimeService(
            channel="ibm_quantum",
            token="my_token",
            backend_specs=fake_backend_specs,
        )
        cloud_service = FakeRuntimeService(
            channel="ibm_cloud",
            token="my_token",
            instance="my_instance",
            backend_specs=fake_backend_specs,
        )
        return [ibm_quantum_service, cloud_service]


@ddt
class TestGetBackend(IBMTestCase):
    """Test getting a backend via ibm_quantum api."""

    def test_get_common_backend(self):
        """Test getting a backend that is in default and non-default hgp."""
        service = FakeRuntimeService(channel="ibm_quantum", token="my_token")
        backend = service.backend(FakeRuntimeService.DEFAULT_COMMON_BACKEND)
        self.assertEqual(backend._instance, list(service._hgps.keys())[0])

    def test_get_unique_backend_default_hgp(self):
        """Test getting a backend in the default hgp."""
        service = FakeRuntimeService(channel="ibm_quantum", token="my_token")
        backend_name = FakeRuntimeService.DEFAULT_UNIQUE_BACKEND_PREFIX + "0"
        backend = service.backend(backend_name)
        self.assertEqual(backend._instance, list(service._hgps.keys())[0])

    def test_get_unique_backend_non_default_hgp(self):
        """Test getting a backend in the non default hgp."""
        service = FakeRuntimeService(channel="ibm_quantum", token="my_token")
        backend_name = FakeRuntimeService.DEFAULT_UNIQUE_BACKEND_PREFIX + "1"
        backend = service.backend(backend_name)
        self.assertEqual(backend._instance, list(service._hgps.keys())[1])

    def test_get_phantom_backend(self):
        """Test getting a phantom backend."""
        service = FakeRuntimeService(channel="ibm_quantum", token="my_token")
        with self.assertRaises(QiskitBackendNotFoundError):
            service.backend("phantom")

    def test_get_backend_by_hgp(self):
        """Test getting a backend by hgp."""
        hgp = FakeRuntimeService.DEFAULT_HGPS[1]
        backend_name = FakeRuntimeService.DEFAULT_COMMON_BACKEND
        service = FakeRuntimeService(channel="ibm_quantum", token="my_token")
        backend = service.backend(backend_name, instance=hgp)
        self.assertEqual(backend._instance, hgp)

    def test_get_backend_by_bad_hgp(self):
        """Test getting a backend not in hgp."""
        hgp = FakeRuntimeService.DEFAULT_HGPS[1]
        backend_name = FakeRuntimeService.DEFAULT_UNIQUE_BACKEND_PREFIX + "0"
        service = FakeRuntimeService(channel="ibm_quantum", token="my_token")
        with self.assertRaises(QiskitBackendNotFoundError):
            _ = service.backend(backend_name, instance=hgp)

    @named_data(
        ("with_fractional", True),
        ("without_fractional", False),
    )
    def test_get_backend_with_fractional_optin(self, use_fractional):
        """Test getting backend with fractional gate opt-in.

        This test can be modified when the IBM backend architecture changes in future.
        In our backend as of today, fractional gates and dynamic circuits are
        only exclusively supported.

        This test is originally written in 2024.05.31
        """
        service = FakeRuntimeService(
            channel="ibm_quantum",
            token="my_token",
            backend_specs=[FakeApiBackendSpecs(backend_name="FakeFractionalBackend")],
        )
        test_backend = service.backends("fake_fractional", use_fractional_gates=use_fractional)[0]
        self.assertEqual(
            "rx" in test_backend.target,
            use_fractional,
        )
        self.assertEqual(
            "rzx" in test_backend.target,
            use_fractional,
        )
        self.assertEqual(
            "if_else" in test_backend.target.operation_names,
            not use_fractional,
        )
        self.assertEqual(
            "while_loop" in test_backend.target.operation_names,
            not use_fractional,
        )

    def test_backend_with_and_without_fractional_from_same_service(self):
        """Test getting backend with and without fractional gates from the same service.

        Backend with and without opt-in must be different object.
        """
        service = FakeRuntimeService(
            channel="ibm_quantum",
            token="my_token",
            backend_specs=[FakeApiBackendSpecs(backend_name="FakeFractionalBackend")],
        )

        backend_with_fg = service.backend("fake_fractional", use_fractional_gates=True)
        self.assertIn("rx", backend_with_fg.target)

        backend_without_fg = service.backend("fake_fractional", use_fractional_gates=False)
        self.assertNotIn("rx", backend_without_fg.target)
        self.assertIn("rx", backend_with_fg.target)

        self.assertIsNot(backend_with_fg, backend_without_fg)
