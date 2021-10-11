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

"""Tests for the IBMProvider class."""

from datetime import datetime
import os
from unittest import skipIf, mock
from configparser import ConfigParser
from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister
from qiskit.test import providers, slow_test
from qiskit.compiler import transpile
from qiskit.providers.exceptions import QiskitBackendNotFoundError
from qiskit.providers.models.backendproperties import BackendProperties

from qiskit_ibm.ibm_backend import IBMSimulator, IBMBackend
from qiskit_ibm.ibm_backend_service import IBMBackendService
from qiskit_ibm.experiment import IBMExperimentService
from qiskit_ibm.random.ibm_random_service import IBMRandomService
from qiskit_ibm.ibm_provider import IBMProvider
from qiskit_ibm import ibm_provider
from qiskit_ibm.api.exceptions import RequestsApiError
from qiskit_ibm.api.clients import AccountClient
from qiskit_ibm.exceptions import (IBMProviderError, IBMProviderValueError,
                                   IBMProviderCredentialsInvalidUrl,
                                   IBMProviderCredentialsInvalidToken,
                                   IBMProviderCredentialsNotFound)
from qiskit_ibm.credentials.hubgroupproject import HubGroupProject
from qiskit_ibm.apiconstants import QISKIT_IBM_API_URL

from ..ibm_test_case import IBMTestCase
from ..decorators import requires_device, requires_provider, requires_qe_access
from ..contextmanagers import custom_qiskitrc, no_envs, CREDENTIAL_ENV_VARS
from ..utils import get_provider

API_URL = 'https://api.quantum-computing.ibm.com/api'
AUTH_URL = 'https://auth.quantum-computing.ibm.com/api'


class TestIBMProviderEnableAccount(IBMTestCase):
    """Tests for IBMProvider."""

    # Enable Account Tests

    @requires_qe_access
    def test_provider_init_token(self, qe_token, qe_url):
        """Test initializing IBMProvider with only API token."""
        # pylint: disable=unused-argument
        provider = IBMProvider(token=qe_token)
        self.assertIsInstance(provider, IBMProvider)
        self.assertEqual(provider.credentials.token, qe_token)
        self.assertEqual(provider.credentials.hub, 'ibm-q')
        self.assertEqual(provider.credentials.group, 'open')
        self.assertEqual(provider.credentials.project, 'main')

    @requires_qe_access
    def test_provider_init_token_url_hub(self, qe_token, qe_url):
        """Test initializing IBMProvider with API token, URL and Hub."""
        provider = IBMProvider(token=qe_token, url=qe_url, hub='ibm-q')
        self.assertIsInstance(provider, IBMProvider)
        self.assertEqual(provider.credentials.token, qe_token)
        self.assertEqual(provider.credentials.hub, 'ibm-q')
        self.assertEqual(provider.credentials.group, 'open')
        self.assertEqual(provider.credentials.project, 'main')

    @requires_qe_access
    def test_provider_init_token_url_group(self, qe_token, qe_url):
        """Test initializing IBMProvider with API token, URL and Group."""
        provider = IBMProvider(token=qe_token, url=qe_url, group='open')
        self.assertIsInstance(provider, IBMProvider)
        self.assertEqual(provider.credentials.token, qe_token)
        self.assertEqual(provider.credentials.hub, 'ibm-q')
        self.assertEqual(provider.credentials.group, 'open')
        self.assertEqual(provider.credentials.project, 'main')

    @requires_qe_access
    def test_provider_init_token_url_project(self, qe_token, qe_url):
        """Test initializing IBMProvider with API token, URL and Project."""
        provider = IBMProvider(token=qe_token, url=qe_url, project='main')
        self.assertIsInstance(provider, IBMProvider)
        self.assertEqual(provider.credentials.token, qe_token)
        self.assertEqual(provider.credentials.hub, 'ibm-q')
        self.assertEqual(provider.credentials.group, 'open')
        self.assertEqual(provider.credentials.project, 'main')

    @requires_qe_access
    def test_provider_init_non_default_provider(self, qe_token, qe_url):
        """Test initializing IBMProvider with a non default provider."""
        non_default_provider = get_provider(qe_token, qe_url, default=False)
        enabled_provider = IBMProvider(
            token=qe_token, url=qe_url,
            hub=non_default_provider.credentials.hub,
            group=non_default_provider.credentials.group,
            project=non_default_provider.credentials.project)
        self.assertEqual(non_default_provider, enabled_provider)

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
            IBMProvider._disable_account()
            IBMProvider(qe_token, qe_url, proxies=proxies)
        self.assertIn('ProxyError', str(context_manager.exception))

    def test_provider_init_non_auth_url(self):
        """Test initializing IBMProvider with a non-auth URL."""
        qe_token = 'invalid'
        qe_url = API_URL

        with self.assertRaises(IBMProviderCredentialsInvalidUrl) as context_manager:
            IBMProvider(token=qe_token, url=qe_url)

        self.assertIn('authentication URL', str(context_manager.exception))

    def test_provider_init_non_auth_url_with_hub(self):
        """Test initializing IBMProvider with a non-auth URL containing h/g/p."""
        qe_token = 'invalid'
        qe_url = API_URL + '/Hubs/X/Groups/Y/Projects/Z'

        with self.assertRaises(IBMProviderCredentialsInvalidUrl) as context_manager:
            IBMProvider(token=qe_token, url=qe_url)

        self.assertIn('authentication URL', str(context_manager.exception))

    def test_provider_init_no_credentials(self):
        """Test initializing IBMProvider with no credentials."""
        with custom_qiskitrc(), \
             self.assertRaises(IBMProviderCredentialsNotFound) as context_manager, \
             no_envs(CREDENTIAL_ENV_VARS):
            IBMProvider()

        self.assertIn('No IBM Quantum credentials found.', str(context_manager.exception))

    @requires_qe_access
    def test_discover_backend_failed(self, qe_token, qe_url):
        """Test discovering backends failed."""
        with mock.patch.object(AccountClient, 'list_backends',
                               return_value=[{'backend_name': 'bad_backend'}]):
            with self.assertLogs(ibm_provider.logger, level='WARNING') as context_manager:
                IBMProvider._disable_account()
                IBMProvider(qe_token, qe_url)
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
            IBMProvider.save_account(self.token, url=QISKIT_IBM_API_URL)
            stored_cred = IBMProvider.saved_account()

        self.assertEqual(stored_cred['token'], self.token)
        self.assertEqual(stored_cred['url'], QISKIT_IBM_API_URL)

    @requires_qe_access
    def test_provider_init_saved_account(self, qe_token, qe_url):
        """Test initializing IBMProvider with credentials from qiskitrc file."""
        if qe_url != QISKIT_IBM_API_URL:
            # save expects an auth production URL.
            self.skipTest('Test requires production auth URL')

        with custom_qiskitrc(), no_envs(CREDENTIAL_ENV_VARS):
            IBMProvider.save_account(qe_token, url=qe_url)
            provider = IBMProvider()

        self.assertIsInstance(provider, IBMProvider)
        self.assertEqual(provider.credentials.token, qe_token)
        self.assertEqual(provider.credentials.auth_url, qe_url)
        self.assertEqual(provider.credentials.hub, 'ibm-q')
        self.assertEqual(provider.credentials.group, 'open')
        self.assertEqual(provider.credentials.project, 'main')

    def test_save_account_specified_provider(self):
        """Test saving an account with a specified provider."""
        default_hgp_to_save = 'ibm-q/open/main'

        with custom_qiskitrc() as custom_qiskitrc_cm:
            hgp = HubGroupProject.from_stored_format(default_hgp_to_save)
            IBMProvider.save_account(token=self.token, url=QISKIT_IBM_API_URL,
                                     hub=hgp.hub, group=hgp.group, project=hgp.project)

            # Ensure the `default_provider` name was written to the config file.
            config_parser = ConfigParser()
            config_parser.read(custom_qiskitrc_cm.tmp_file.name)

            for name in config_parser.sections():
                single_credentials = dict(config_parser.items(name))
                self.assertIn('default_provider', single_credentials)
                self.assertEqual(single_credentials['default_provider'], default_hgp_to_save)

    def test_save_account_specified_provider_invalid(self):
        """Test saving an account without specifying all the hub/group/project fields."""
        invalid_hgps_to_save = [HubGroupProject('', 'default_group', ''),
                                HubGroupProject('default_hub', None, 'default_project')]
        for invalid_hgp in invalid_hgps_to_save:
            with self.subTest(invalid_hgp=invalid_hgp), custom_qiskitrc():
                with self.assertRaises(IBMProviderValueError) as context_manager:
                    IBMProvider.save_account(token=self.token,
                                             url=QISKIT_IBM_API_URL,
                                             hub=invalid_hgp.hub,
                                             group=invalid_hgp.group,
                                             project=invalid_hgp.project)
                self.assertIn('The hub, group, and project parameters must all be specified',
                              str(context_manager.exception))

    def test_delete_account(self):
        """Test deleting an account."""
        with custom_qiskitrc():
            IBMProvider.save_account(self.token, url=QISKIT_IBM_API_URL)
            IBMProvider.delete_account()
            stored_cred = IBMProvider.saved_account()

        self.assertEqual(len(stored_cred), 0)

    @requires_qe_access
    def test_load_account_saved_provider(self, qe_token, qe_url):
        """Test loading an account that contains a saved provider."""
        if qe_url != QISKIT_IBM_API_URL:
            # .save_account() expects an auth production URL.
            self.skipTest('Test requires production auth URL')

        # Get a non default provider.
        non_default_provider = get_provider(qe_token, qe_url, default=False)

        with custom_qiskitrc(), no_envs(CREDENTIAL_ENV_VARS):
            IBMProvider.save_account(token=qe_token, url=qe_url,
                                     hub=non_default_provider.credentials.hub,
                                     group=non_default_provider.credentials.group,
                                     project=non_default_provider.credentials.project)
            saved_provider = IBMProvider()
            if saved_provider != non_default_provider:
                # Prevent tokens from being logged.
                saved_provider.credentials.token = None
                non_default_provider.credentials.token = None
                self.fail("loaded default provider ({}) != expected ({})".format(
                    saved_provider.credentials.__dict__,
                    non_default_provider.credentials.__dict__))

        self.assertEqual(saved_provider.credentials.token, qe_token)
        self.assertEqual(saved_provider.credentials.auth_url, qe_url)
        self.assertEqual(saved_provider.credentials.hub, non_default_provider.credentials.hub)
        self.assertEqual(saved_provider.credentials.group, non_default_provider.credentials.group)
        self.assertEqual(saved_provider.credentials.project,
                         non_default_provider.credentials.project)

    @requires_qe_access
    def test_load_account_saved_provider_invalid_hgp(self, qe_token, qe_url):
        """Test loading an account that contains a saved provider that does not exist."""
        if qe_url != QISKIT_IBM_API_URL:
            # .save_account() expects an auth production URL.
            self.skipTest('Test requires production auth URL')

        # Hub, group, project in correct format but does not exists.
        invalid_hgp_to_store = 'invalid_hub/invalid_group/invalid_project'
        with custom_qiskitrc(), no_envs(CREDENTIAL_ENV_VARS):
            hgp = HubGroupProject.from_stored_format(invalid_hgp_to_store)
            with self.assertRaises(IBMProviderError) as context_manager:
                IBMProvider.save_account(token=qe_token, url=qe_url,
                                         hub=hgp.hub, group=hgp.group, project=hgp.project)
                IBMProvider()

            self.assertIn('No provider matches the specified criteria',
                          str(context_manager.exception))

    def test_load_account_saved_provider_invalid_format(self):
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
                    IBMProvider.save_account(token=self.token, url=QISKIT_IBM_API_URL)
                    # Add an invalid provider field to the account stored.
                    with open(temp_qiskitrc.tmp_file.name, 'a') as _file:
                        _file.write('default_provider = {}'.format(invalid_hgp))
                    # Ensure an error is raised if the stored provider is in an invalid format.
                    with self.assertRaises(IBMProviderError) as context_manager:
                        IBMProvider()
                    self.assertIn(error_message, str(context_manager.exception))

    @requires_qe_access
    def test_disable_account(self, qe_token, qe_url):
        """Test disabling an account """
        IBMProvider(qe_token, qe_url)
        IBMProvider._disable_account()
        self.assertFalse(IBMProvider._providers)

    @requires_qe_access
    def test_active_account(self, qe_token, qe_url):
        """Test get active account """
        IBMProvider._disable_account()
        self.assertIsNone(IBMProvider.active_account())

        IBMProvider(qe_token, qe_url)
        active_account = IBMProvider.active_account()
        self.assertIsNotNone(active_account)
        self.assertEqual(active_account['token'], qe_token)
        self.assertEqual(active_account['url'], qe_url)

    def test_save_token_invalid(self):
        """Test saving an account with invalid tokens. See #391."""
        invalid_tokens = [None, '', 0]
        for invalid_token in invalid_tokens:
            with self.subTest(invalid_token=invalid_token):
                with self.assertRaises(IBMProviderCredentialsInvalidToken) as context_manager:
                    IBMProvider.save_account(token=invalid_token, url=QISKIT_IBM_API_URL)
                self.assertIn('Invalid IBM Quantum token found',
                              str(context_manager.exception))


class TestIBMProviderProvider(IBMTestCase):
    """Tests for IBMProvider provider related methods."""

    @requires_qe_access
    def _get_provider(self, qe_token=None, qe_url=None):
        """Return default provider."""
        return IBMProvider(qe_token, qe_url)

    def setUp(self):
        """Initial test setup."""
        super().setUp()

        self.provider = self._get_provider()
        self.credentials = self.provider.credentials

    def test_get_provider(self):
        """Test get single provider."""
        provider = IBMProvider._get_provider(
            hub=self.credentials.hub,
            group=self.credentials.group,
            project=self.credentials.project)
        self.assertEqual(self.provider, provider)

    def test_providers_with_filter(self):
        """Test providers() with a filter."""
        provider = IBMProvider.providers(
            hub=self.credentials.hub,
            group=self.credentials.group,
            project=self.credentials.project)[0]
        self.assertEqual(self.provider, provider)

    def test_providers_no_filter(self):
        """Test providers() without a filter."""
        providers_list = IBMProvider.providers()
        self.assertIn(self.provider, providers_list)


class TestIBMProviderServices(IBMTestCase, providers.ProviderTestCase):
    """Tests for services provided by the IBMProvider class."""

    provider_cls = IBMProvider
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
    def _get_provider(self, provider):
        """Return an instance of a provider."""
        # pylint: disable=arguments-differ
        return provider

    def test_remote_backends_exist_real_device(self):
        """Test if there are remote backends that are devices."""
        remotes = self.provider.backends(simulator=False)
        self.assertTrue(remotes)

    def test_remote_backends_exist_simulator(self):
        """Test if there are remote backends that are simulators."""
        remotes = self.provider.backends(simulator=True)
        self.assertTrue(remotes)

    def test_remote_backends_instantiate_simulators(self):
        """Test if remote backends that are simulators are an ``IBMSimulator`` instance."""
        remotes = self.provider.backends(simulator=True)
        for backend in remotes:
            with self.subTest(backend=backend):
                self.assertIsInstance(backend, IBMSimulator)

    def test_remote_backend_status(self):
        """Test backend_status."""
        remotes = self.provider.backends()
        for backend in remotes:
            _ = backend.status()

    def test_remote_backend_configuration(self):
        """Test backend configuration."""
        remotes = self.provider.backends()
        for backend in remotes:
            _ = backend.configuration()

    def test_remote_backend_properties(self):
        """Test backend properties."""
        remotes = self.provider.backends(simulator=False)
        for backend in remotes:
            properties = backend.properties()
            if backend.configuration().simulator:
                self.assertEqual(properties, None)

    def test_headers_in_result_sims(self):
        """Test that the qobj headers are passed onto the results for sims."""
        backend = self.provider.get_backend('ibmq_qasm_simulator')

        custom_header = {'x': 1, 'y': [1, 2, 3], 'z': {'a': 4}}
        circuits = transpile(self.qc1, backend=backend)

        # TODO Use circuit metadata for individual header when terra PR-5270 is released.
        # qobj.experiments[0].header.some_field = 'extra info'

        job = backend.run(circuits, header=custom_header)
        result = job.result()
        self.assertTrue(custom_header.items() <= job.header().items())
        self.assertTrue(custom_header.items() <= result.header.to_dict().items())
        # self.assertEqual(result.results[0].header.some_field, 'extra info')

    @slow_test
    @requires_device
    def test_headers_in_result_devices(self, backend):
        """Test that the qobj headers are passed onto the results for devices."""
        custom_header = {'x': 1, 'y': [1, 2, 3], 'z': {'a': 4}}

        # TODO Use circuit metadata for individual header when terra PR-5270 is released.
        # qobj.experiments[0].header.some_field = 'extra info'

        job = backend.run(transpile(self.qc1, backend=backend), header=custom_header)
        job.wait_for_final_state(wait=300, callback=self.simple_job_callback)
        result = job.result()
        self.assertTrue(custom_header.items() <= job.header().items())
        self.assertTrue(custom_header.items() <= result.header.to_dict().items())
        # self.assertEqual(result.results[0].header.some_field, 'extra info')

    def test_aliases(self):
        """Test that display names of devices map the regular names."""
        aliased_names = self.provider.backend._aliased_backend_names()

        for display_name, backend_name in aliased_names.items():
            with self.subTest(display_name=display_name,
                              backend_name=backend_name):
                try:
                    backend_by_name = self.provider.get_backend(backend_name)
                except QiskitBackendNotFoundError:
                    # The real name of the backend might not exist
                    pass
                else:
                    backend_by_display_name = self.provider.get_backend(
                        display_name)
                    self.assertEqual(backend_by_name, backend_by_display_name)
                    self.assertEqual(
                        backend_by_display_name.name(), backend_name)

    def test_remote_backend_properties_filter_date(self):
        """Test backend properties filtered by date."""
        backends = self.provider.backends(simulator=False)

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
        provider_backends = {back for back in dir(self.provider.backend)
                             if isinstance(getattr(self.provider.backend, back), IBMBackend)}
        backends = {back.name().lower() for back in self.provider._backends.values()}
        self.assertEqual(provider_backends, backends)

    def test_provider_services(self):
        """Test provider services."""
        services = self.provider.services()
        self.assertIn('backend', services)
        self.assertIsInstance(services['backend'], IBMBackendService)
        self.assertIsInstance(self.provider.service('backend'), IBMBackendService)
        self.assertIsInstance(self.provider.backend, IBMBackendService)

        if 'experiment' in services:
            self.assertIsInstance(self.provider.service('experiment'), IBMExperimentService)
            self.assertIsInstance(self.provider.experiment, IBMExperimentService)
        if 'random' in services:
            self.assertIsInstance(self.provider.service('random'), IBMRandomService)
            self.assertIsInstance(self.provider.random, IBMRandomService)
