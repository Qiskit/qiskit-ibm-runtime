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

"""Tests for the IBMRuntimeService class."""

from datetime import datetime
from unittest import mock

from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister
from qiskit.providers.exceptions import QiskitBackendNotFoundError
from qiskit.providers.models.backendproperties import BackendProperties

from qiskit_ibm_runtime import IBMRuntimeService
from qiskit_ibm_runtime import hub_group_project
from qiskit_ibm_runtime.api.clients import AccountClient
from qiskit_ibm_runtime.api.exceptions import RequestsApiError
from qiskit_ibm_runtime.exceptions import (
    IBMProviderCredentialsInvalidUrl,
)
from qiskit_ibm_runtime.ibm_backend import IBMSimulator, IBMBackend
from ..decorators import requires_qe_access, requires_provider
from ..ibm_test_case import IBMTestCase

API_URL = "https://api.quantum-computing.ibm.com/api"
AUTH_URL = "https://auth.quantum-computing.ibm.com/api"


class TestIBMProviderEnableAccount(IBMTestCase):
    """Tests for IBMRuntimeService."""

    # Enable Account Tests

    @requires_qe_access
    def test_provider_init_token(self, qe_token, qe_url):
        """Test initializing IBMRuntimeService with only API token."""
        # pylint: disable=unused-argument
        service = IBMRuntimeService(auth="legacy", token=qe_token)
        self.assertIsInstance(service, IBMRuntimeService)
        self.assertEqual(service._default_hgp.credentials.token, qe_token)

    @requires_qe_access
    def test_pass_unreachable_proxy(self, qe_token, qe_url):
        """Test using an unreachable proxy while enabling an account."""
        proxies = {
            "urls": {
                "http": "http://user:password@127.0.0.1:5678",
                "https": "https://user:password@127.0.0.1:5678",
            }
        }
        with self.assertRaises(RequestsApiError) as context_manager:
            IBMRuntimeService(
                auth="legacy", token=qe_token, url=qe_url, proxies=proxies
            )
        self.assertIn("ProxyError", str(context_manager.exception))

    def test_provider_init_non_auth_url(self):
        """Test initializing IBMRuntimeService with a non-auth URL."""
        qe_token = "invalid"
        qe_url = API_URL

        with self.assertRaises(IBMProviderCredentialsInvalidUrl) as context_manager:
            IBMRuntimeService(auth="legacy", token=qe_token, url=qe_url)

        self.assertIn("authentication URL", str(context_manager.exception))

    def test_provider_init_non_auth_url_with_hub(self):
        """Test initializing IBMRuntimeService with a non-auth URL containing h/g/p."""
        qe_token = "invalid"
        qe_url = API_URL + "/Hubs/X/Groups/Y/Projects/Z"

        with self.assertRaises(IBMProviderCredentialsInvalidUrl) as context_manager:
            IBMRuntimeService(auth="legacy", token=qe_token, url=qe_url)

        self.assertIn("authentication URL", str(context_manager.exception))

    @requires_qe_access
    def test_discover_backend_failed(self, qe_token, qe_url):
        """Test discovering backends failed."""
        with mock.patch.object(
            AccountClient,
            "list_backends",
            return_value=[{"backend_name": "bad_backend"}],
        ):
            with self.assertLogs(
                hub_group_project.logger, level="WARNING"
            ) as context_manager:
                IBMRuntimeService(auth="legacy", token=qe_token, url=qe_url)
        self.assertIn("bad_backend", str(context_manager.output))


class TestIBMProviderHubGroupProject(IBMTestCase):
    """Tests for IBMRuntimeService HubGroupProject related methods."""

    @requires_qe_access
    def _initialize_provider(self, qe_token=None, qe_url=None):
        """Initialize and return provider."""
        return IBMRuntimeService(auth="legacy", token=qe_token, url=qe_url)

    def setUp(self):
        """Initial test setup."""
        super().setUp()

        self.service = self._initialize_provider()
        self.credentials = self.service._default_hgp.credentials

    def test_get_hgp(self):
        """Test get single hgp."""
        hgp = self.service._get_hgp(
            hub=self.credentials.hub,
            group=self.credentials.group,
            project=self.credentials.project,
        )
        self.assertEqual(self.service._default_hgp, hgp)

    def test_get_hgps_with_filter(self):
        """Test get hgps with a filter."""
        hgp = self.service._get_hgps(
            hub=self.credentials.hub,
            group=self.credentials.group,
            project=self.credentials.project,
        )[0]
        self.assertEqual(self.service._default_hgp, hgp)

    def test_get_hgps_no_filter(self):
        """Test get hgps without a filter."""
        hgps = self.service._get_hgps()
        self.assertIn(self.service._default_hgp, hgps)


class TestIBMProviderServices(IBMTestCase):
    """Tests for services provided by the IBMRuntimeService class."""

    @requires_provider
    def setUp(self, service, hub, group, project):
        """Initial test setup."""
        # pylint: disable=arguments-differ
        super().setUp()
        self.service = service
        self.hub = hub
        self.group = group
        self.project = project
        qr = QuantumRegister(1)
        cr = ClassicalRegister(1)
        self.qc1 = QuantumCircuit(qr, cr, name="circuit0")
        self.qc1.h(qr[0])
        self.qc1.measure(qr, cr)

    def test_remote_backends_exist_real_device(self):
        """Test if there are remote backends that are devices."""
        remotes = self.service.backends(
            simulator=False, hub=self.hub, group=self.group, project=self.project
        )
        self.assertTrue(remotes)

    def test_remote_backends_exist_simulator(self):
        """Test if there are remote backends that are simulators."""
        remotes = self.service.backends(
            simulator=True, hub=self.hub, group=self.group, project=self.project
        )
        self.assertTrue(remotes)

    def test_remote_backends_instantiate_simulators(self):
        """Test if remote backends that are simulators are an ``IBMSimulator`` instance."""
        remotes = self.service.backends(
            simulator=True, hub=self.hub, group=self.group, project=self.project
        )
        for backend in remotes:
            with self.subTest(backend=backend):
                self.assertIsInstance(backend, IBMSimulator)

    def test_remote_backend_status(self):
        """Test backend_status."""
        remotes = self.service.backends(
            hub=self.hub, group=self.group, project=self.project
        )
        for backend in remotes:
            _ = backend.status()

    def test_remote_backend_configuration(self):
        """Test backend configuration."""
        remotes = self.service.backends(
            hub=self.hub, group=self.group, project=self.project
        )
        for backend in remotes:
            _ = backend.configuration()

    def test_remote_backend_properties(self):
        """Test backend properties."""
        remotes = self.service.backends(
            simulator=False, hub=self.hub, group=self.group, project=self.project
        )
        for backend in remotes:
            properties = backend.properties()
            if backend.configuration().simulator:
                self.assertEqual(properties, None)

    def test_aliases(self):
        """Test that display names of devices map the regular names."""
        aliased_names = self.service._aliased_backend_names()

        for display_name, backend_name in aliased_names.items():
            with self.subTest(display_name=display_name, backend_name=backend_name):
                try:
                    backend_by_name = self.service.get_backend(
                        backend_name,
                        hub=self.hub,
                        group=self.group,
                        project=self.project,
                    )
                except QiskitBackendNotFoundError:
                    # The real name of the backend might not exist
                    pass
                else:
                    backend_by_display_name = self.service.get_backend(display_name)
                    self.assertEqual(backend_by_name, backend_by_display_name)
                    self.assertEqual(backend_by_display_name.name(), backend_name)

    def test_remote_backend_properties_filter_date(self):
        """Test backend properties filtered by date."""
        backends = self.service.backends(
            simulator=False, hub=self.hub, group=self.group, project=self.project
        )

        datetime_filter = datetime(2019, 2, 1).replace(tzinfo=None)
        for backend in backends:
            with self.subTest(backend=backend):
                properties = backend.properties(datetime=datetime_filter)
                if isinstance(properties, BackendProperties):
                    last_update_date = properties.last_update_date.replace(tzinfo=None)
                    self.assertLessEqual(last_update_date, datetime_filter)
                else:
                    self.assertEqual(properties, None)

    def test_provider_backends(self):
        """Test provider_backends have correct attributes."""
        provider_backends = {
            back
            for back in dir(self.service)
            if isinstance(getattr(self.service, back), IBMBackend)
        }
        backends = {back.name().lower() for back in self.service._backends.values()}
        self.assertEqual(provider_backends, backends)
