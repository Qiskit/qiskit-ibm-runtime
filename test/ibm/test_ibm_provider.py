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
import os
from unittest import skipIf, mock
from configparser import ConfigParser
from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister
from qiskit.test import providers, slow_test
from qiskit.compiler import transpile
from qiskit.providers.exceptions import QiskitBackendNotFoundError
from qiskit.providers.models.backendproperties import BackendProperties

from qiskit_ibm_runtime.ibm_backend import IBMSimulator, IBMBackend
from qiskit_ibm_runtime import IBMRuntimeService
from qiskit_ibm_runtime import hub_group_project
from qiskit_ibm_runtime.api.exceptions import RequestsApiError
from qiskit_ibm_runtime.api.clients import AccountClient
from qiskit_ibm_runtime.exceptions import (IBMProviderError, IBMProviderValueError,
                                           IBMProviderCredentialsInvalidUrl,
                                           IBMProviderCredentialsInvalidToken,
                                           IBMProviderCredentialsNotFound)
from qiskit_ibm_runtime.credentials.hub_group_project_id import HubGroupProjectID
from qiskit_ibm_runtime.apiconstants import QISKIT_IBM_RUNTIME_API_URL

from ..ibm_test_case import IBMTestCase
from ..decorators import requires_device, requires_qe_access, requires_provider
from ..contextmanagers import custom_qiskitrc, no_envs, CREDENTIAL_ENV_VARS
from ..utils import get_hgp

API_URL = 'https://api.quantum-computing.ibm.com/api'
AUTH_URL = 'https://auth.quantum-computing.ibm.com/api'


class TestIBMProviderEnableAccount(IBMTestCase):
    """Tests for IBMRuntimeService."""

    # Enable Account Tests

    @requires_qe_access
    def test_provider_init_token(self, qe_token, qe_url):
        """Test initializing IBMRuntimeService with only API token."""
        # pylint: disable=unused-argument
        service = IBMRuntimeService(token=qe_token)
        self.assertIsInstance(service, IBMRuntimeService)
        self.assertEqual(service._default_hgp.credentials.token, qe_token)

    @requires_qe_access
    def test_pass_unreachable_proxy(self, qe_token, qe_url):
        """Test using an unreachable proxy while enabling an account."""
        proxies = {
            'urls': {
                'http': 'http://user:password@127.0.0.1:5678',
                'https': 'https://user:password@127.0.0.1:5678'
            }
        }
        with self.assertRaises(RequestsApiError) as context_manager:
            IBMRuntimeService(qe_token, qe_url, proxies=proxies)
        self.assertIn('ProxyError', str(context_manager.exception))

    def test_provider_init_non_auth_url(self):
        """Test initializing IBMRuntimeService with a non-auth URL."""
        qe_token = 'invalid'
        qe_url = API_URL

        with self.assertRaises(IBMProviderCredentialsInvalidUrl) as context_manager:
            IBMRuntimeService(token=qe_token, url=qe_url)

        self.assertIn('authentication URL', str(context_manager.exception))

    def test_provider_init_non_auth_url_with_hub(self):
        """Test initializing IBMRuntimeService with a non-auth URL containing h/g/p."""
        qe_token = 'invalid'
        qe_url = API_URL + '/Hubs/X/Groups/Y/Projects/Z'

        with self.assertRaises(IBMProviderCredentialsInvalidUrl) as context_manager:
            IBMRuntimeService(token=qe_token, url=qe_url)

        self.assertIn('authentication URL', str(context_manager.exception))

    def test_provider_init_no_credentials(self):
        """Test initializing IBMRuntimeService with no credentials."""
        with custom_qiskitrc(), \
             self.assertRaises(IBMProviderCredentialsNotFound) as context_manager, \
             no_envs(CREDENTIAL_ENV_VARS):
            IBMRuntimeService()

        self.assertIn('No IBM Quantum credentials found.', str(context_manager.exception))

    @requires_qe_access
    def test_discover_backend_failed(self, qe_token, qe_url):
        """Test discovering backends failed."""
        with mock.patch.object(AccountClient, 'list_backends',
                               return_value=[{'backend_name': 'bad_backend'}]):
            with self.assertLogs(hub_group_project.logger, level='WARNING') as context_manager:
                IBMRuntimeService(qe_token, qe_url)
        self.assertIn('bad_backend', str(context_manager.output))


@skipIf(os.name == 'nt', 'Test not supported in Windows')
class TestIBMProviderAccounts(IBMTestCase):
    """Tests for account handling."""

    @classmethod
    def setUpClass(cls):
        """Initial class setup."""
        super().setUpClass()
        cls.token = 'API_TOKEN'

    def test_save_account(self):
        """Test saving an account."""
        with custom_qiskitrc():
            IBMRuntimeService.save_account(self.token, url=QISKIT_IBM_RUNTIME_API_URL)
            stored_cred = IBMRuntimeService.saved_account()

        self.assertEqual(stored_cred['token'], self.token)
        self.assertEqual(stored_cred['url'], QISKIT_IBM_RUNTIME_API_URL)

    @requires_qe_access
    def test_provider_init_saved_account(self, qe_token, qe_url):
        """Test initializing IBMRuntimeService with credentials from qiskitrc file."""
        if qe_url != QISKIT_IBM_RUNTIME_API_URL:
            # save expects an auth production URL.
            self.skipTest('Test requires production auth URL')

        with custom_qiskitrc(), no_envs(CREDENTIAL_ENV_VARS):
            IBMRuntimeService.save_account(qe_token, url=qe_url)
            service = IBMRuntimeService()

        self.assertIsInstance(service, IBMRuntimeService)
        self.assertEqual(service._default_hgp.credentials.token, qe_token)
        self.assertEqual(service._default_hgp.credentials.auth_url, qe_url)

    def test_save_account_specified_provider(self):
        """Test saving an account with a specified hub/group/project."""
        default_hgp_to_save = 'ibm-q/open/main'

        with custom_qiskitrc() as custom_qiskitrc_cm:
            hgp_id = HubGroupProjectID.from_stored_format(default_hgp_to_save)
            IBMRuntimeService.save_account(token=self.token, url=QISKIT_IBM_RUNTIME_API_URL,
                                           hub=hgp_id.hub, group=hgp_id.group,
                                           project=hgp_id.project)

            # Ensure the `default_provider` name was written to the config file.
            config_parser = ConfigParser()
            config_parser.read(custom_qiskitrc_cm.tmp_file.name)

            for name in config_parser.sections():
                single_credentials = dict(config_parser.items(name))
                self.assertIn('default_provider', single_credentials)
                self.assertEqual(single_credentials['default_provider'], default_hgp_to_save)

    def test_save_account_specified_provider_invalid(self):
        """Test saving an account without specifying all the hub/group/project fields."""
        invalid_hgp_ids_to_save = [HubGroupProjectID('', 'default_group', ''),
                                   HubGroupProjectID('default_hub', None, 'default_project')]
        for invalid_hgp_id in invalid_hgp_ids_to_save:
            with self.subTest(invalid_hgp_id=invalid_hgp_id), custom_qiskitrc():
                with self.assertRaises(IBMProviderValueError) as context_manager:
                    IBMRuntimeService.save_account(token=self.token,
                                                   url=QISKIT_IBM_RUNTIME_API_URL,
                                                   hub=invalid_hgp_id.hub,
                                                   group=invalid_hgp_id.group,
                                                   project=invalid_hgp_id.project)
                self.assertIn('The hub, group, and project parameters must all be specified',
                              str(context_manager.exception))

    def test_delete_account(self):
        """Test deleting an account."""
        with custom_qiskitrc():
            IBMRuntimeService.save_account(self.token, url=QISKIT_IBM_RUNTIME_API_URL)
            IBMRuntimeService.delete_account()
            stored_cred = IBMRuntimeService.saved_account()

        self.assertEqual(len(stored_cred), 0)

    @requires_qe_access
    def test_load_account_saved_provider(self, qe_token, qe_url):
        """Test loading an account that contains a saved hub/group/project."""
        if qe_url != QISKIT_IBM_RUNTIME_API_URL:
            # .save_account() expects an auth production URL.
            self.skipTest('Test requires production auth URL')

        # Get a non default hub/group/project.
        non_default_hgp = get_hgp(qe_token, qe_url, default=False)

        with custom_qiskitrc(), no_envs(CREDENTIAL_ENV_VARS):
            IBMRuntimeService.save_account(token=qe_token, url=qe_url,
                                           hub=non_default_hgp.credentials.hub,
                                           group=non_default_hgp.credentials.group,
                                           project=non_default_hgp.credentials.project)
            saved_provider = IBMRuntimeService()
            if saved_provider._default_hgp != non_default_hgp:
                # Prevent tokens from being logged.
                saved_provider._default_hgp.credentials.token = None
                non_default_hgp.credentials.token = None
                self.fail("loaded default hgp ({}) != expected ({})".format(
                    saved_provider._default_hgp.credentials.__dict__,
                    non_default_hgp.credentials.__dict__))

        self.assertEqual(saved_provider._default_hgp.credentials.token, qe_token)
        self.assertEqual(saved_provider._default_hgp.credentials.auth_url, qe_url)
        self.assertEqual(saved_provider._default_hgp.credentials.hub,
                         non_default_hgp.credentials.hub)
        self.assertEqual(saved_provider._default_hgp.credentials.group,
                         non_default_hgp.credentials.group)
        self.assertEqual(saved_provider._default_hgp.credentials.project,
                         non_default_hgp.credentials.project)

    @requires_qe_access
    def test_load_saved_account_invalid_hgp(self, qe_token, qe_url):
        """Test loading an account that contains a saved hub/group/project that does not exist."""
        if qe_url != QISKIT_IBM_RUNTIME_API_URL:
            # .save_account() expects an auth production URL.
            self.skipTest('Test requires production auth URL')

        # Hub, group, project in correct format but does not exists.
        invalid_hgp_to_store = 'invalid_hub/invalid_group/invalid_project'
        with custom_qiskitrc(), no_envs(CREDENTIAL_ENV_VARS):
            hgp_id = HubGroupProjectID.from_stored_format(invalid_hgp_to_store)
            with self.assertRaises(IBMProviderError) as context_manager:
                IBMRuntimeService.save_account(token=qe_token, url=qe_url, hub=hgp_id.hub,
                                               group=hgp_id.group, project=hgp_id.project)
                IBMRuntimeService()

            self.assertIn('No hub/group/project matches the specified criteria',
                          str(context_manager.exception))

    def test_load_saved_account_invalid_hgp_format(self):
        """Test loading an account that contains a saved provider in an invalid format."""
        # Format {'test_case_input': 'error message from raised exception'}
        invalid_hgps = {
            'hub_group_project': 'Use the "<hub_name>/<group_name>/<project_name>" format',
            'default_hub//default_project': 'Every field must be specified',
            'default_hub/default_group/': 'Every field must be specified'
        }

        for invalid_hgp, error_message in invalid_hgps.items():
            with self.subTest(invalid_hgp=invalid_hgp):
                with custom_qiskitrc() as temp_qiskitrc, \
                        no_envs(CREDENTIAL_ENV_VARS):
                    # Save the account.
                    IBMRuntimeService.save_account(token=self.token, url=QISKIT_IBM_RUNTIME_API_URL)
                    # Add an invalid provider field to the account stored.
                    with open(temp_qiskitrc.tmp_file.name, 'a') as _file:
                        _file.write('default_provider = {}'.format(invalid_hgp))
                    # Ensure an error is raised if the stored provider is in an invalid format.
                    with self.assertRaises(IBMProviderError) as context_manager:
                        IBMRuntimeService()
                    self.assertIn(error_message, str(context_manager.exception))

    @requires_qe_access
    def test_active_account(self, qe_token, qe_url):
        """Test get active account """
        service = IBMRuntimeService(qe_token, qe_url)
        active_account = service.active_account()
        self.assertIsNotNone(active_account)
        self.assertEqual(active_account['token'], qe_token)
        self.assertEqual(active_account['url'], qe_url)

    def test_save_token_invalid(self):
        """Test saving an account with invalid tokens. See #391."""
        invalid_tokens = [None, '', 0]
        for invalid_token in invalid_tokens:
            with self.subTest(invalid_token=invalid_token):
                with self.assertRaises(IBMProviderCredentialsInvalidToken) as context_manager:
                    IBMRuntimeService.save_account(token=invalid_token,
                                                   url=QISKIT_IBM_RUNTIME_API_URL)
                self.assertIn('Invalid IBM Quantum token found',
                              str(context_manager.exception))


class TestIBMProviderHubGroupProject(IBMTestCase):
    """Tests for IBMRuntimeService HubGroupProject related methods."""

    @requires_qe_access
    def _initialize_provider(self, qe_token=None, qe_url=None):
        """Initialize and return provider."""
        return IBMRuntimeService(qe_token, qe_url)

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
            project=self.credentials.project)
        self.assertEqual(self.service._default_hgp, hgp)

    def test_get_hgps_with_filter(self):
        """Test get hgps with a filter."""
        hgp = self.service._get_hgps(
            hub=self.credentials.hub,
            group=self.credentials.group,
            project=self.credentials.project)[0]
        self.assertEqual(self.service._default_hgp, hgp)

    def test_get_hgps_no_filter(self):
        """Test get hgps without a filter."""
        hgps = self.service._get_hgps()
        self.assertIn(self.service._default_hgp, hgps)


class TestIBMProviderServices(IBMTestCase, providers.ProviderTestCase):
    """Tests for services provided by the IBMRuntimeService class."""

    provider_cls = IBMRuntimeService
    backend_name = 'ibmq_qasm_simulator'

    def setUp(self):
        """Initial test setup."""
        super().setUp()
        qr = QuantumRegister(1)
        cr = ClassicalRegister(1)
        self.qc1 = QuantumCircuit(qr, cr, name='circuit0')
        self.qc1.h(qr[0])
        self.qc1.measure(qr, cr)

    @requires_provider
    def _get_provider(self, provider, hub, group, project):
        """Return an instance of a provider."""
        # pylint: disable=arguments-differ
        self.hub = hub
        self.group = group
        self.project = project
        return provider

    def test_remote_backends_exist_real_device(self):
        """Test if there are remote backends that are devices."""
        remotes = self.service.backends(simulator=False, hub=self.hub,
                                        group=self.group, project=self.project)
        self.assertTrue(remotes)

    def test_remote_backends_exist_simulator(self):
        """Test if there are remote backends that are simulators."""
        remotes = self.service.backends(simulator=True, hub=self.hub,
                                        group=self.group, project=self.project)
        self.assertTrue(remotes)

    def test_remote_backends_instantiate_simulators(self):
        """Test if remote backends that are simulators are an ``IBMSimulator`` instance."""
        remotes = self.service.backends(simulator=True, hub=self.hub,
                                        group=self.group, project=self.project)
        for backend in remotes:
            with self.subTest(backend=backend):
                self.assertIsInstance(backend, IBMSimulator)

    def test_remote_backend_status(self):
        """Test backend_status."""
        remotes = self.service.backends(hub=self.hub, group=self.group, project=self.project)
        for backend in remotes:
            _ = backend.status()

    def test_remote_backend_configuration(self):
        """Test backend configuration."""
        remotes = self.service.backends(hub=self.hub, group=self.group, project=self.project)
        for backend in remotes:
            _ = backend.configuration()

    def test_remote_backend_properties(self):
        """Test backend properties."""
        remotes = self.service.backends(simulator=False, hub=self.hub,
                                        group=self.group, project=self.project)
        for backend in remotes:
            properties = backend.properties()
            if backend.configuration().simulator:
                self.assertEqual(properties, None)

    def test_headers_in_result_sims(self):
        """Test that the qobj headers are passed onto the results for sims."""
        backend = self.service.get_backend('ibmq_qasm_simulator', hub=self.hub, group=self.group,
                                           project=self.project)

        custom_header = {'x': 1, 'y': [1, 2, 3], 'z': {'a': 4}}
        circuits = transpile(self.qc1, backend=backend)

        # TODO Use circuit metadata for individual header when terra PR-5270 is released.
        # qobj.experiments[0].header.some_field = 'extra info'

        job = backend.run(circuits, header=custom_header)
        result = job.result()
        self.assertTrue(custom_header.items() <= job.header().items())
        self.assertTrue(custom_header.items() <= result.header.to_dict().items())
        # self.assertEqual(result.results[0].header.some_field, 'extra info')

    def test_aliases(self):
        """Test that display names of devices map the regular names."""
        aliased_names = self.service.backend._aliased_backend_names()

        for display_name, backend_name in aliased_names.items():
            with self.subTest(display_name=display_name,
                              backend_name=backend_name):
                try:
                    backend_by_name = self.service.get_backend(backend_name, hub=self.hub,
                                                               group=self.group,
                                                               project=self.project)
                except QiskitBackendNotFoundError:
                    # The real name of the backend might not exist
                    pass
                else:
                    backend_by_display_name = self.service.get_backend(
                        display_name)
                    self.assertEqual(backend_by_name, backend_by_display_name)
                    self.assertEqual(
                        backend_by_display_name.name(), backend_name)

    def test_remote_backend_properties_filter_date(self):
        """Test backend properties filtered by date."""
        backends = self.service.backends(simulator=False, hub=self.hub,
                                         group=self.group, project=self.project)

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
        provider_backends = {back for back in dir(self.service.backend)
                             if isinstance(getattr(self.service.backend, back), IBMBackend)}
        backends = {back.name().lower() for back in self.service.backend._backends.values()}
        self.assertEqual(provider_backends, backends)
