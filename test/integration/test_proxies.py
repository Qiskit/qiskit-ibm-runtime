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

"""Tests for the proxy support."""

import subprocess
import urllib

from requests.exceptions import ProxyError

from qiskit_ibm_runtime.proxies import ProxyConfiguration
from qiskit_ibm_runtime import QiskitRuntimeService
from qiskit_ibm_runtime.api.client_parameters import ClientParameters
from qiskit_ibm_runtime.api.clients import AuthClient, VersionClient
from qiskit_ibm_runtime.api.clients.runtime import RuntimeClient
from qiskit_ibm_runtime.api.exceptions import RequestsApiError

from ..ibm_test_case import IBMTestCase
from ..decorators import IntegrationTestDependencies, integration_test_setup

ADDRESS = "127.0.0.1"
PORT = 8085
VALID_PROXIES = {"https": "http://{}:{}".format(ADDRESS, PORT)}
INVALID_PORT_PROXIES = {"https": "http://{}:{}".format(ADDRESS, "6666")}
INVALID_ADDRESS_PROXIES = {"https": "http://{}:{}".format("invalid", PORT)}


class TestProxies(IBMTestCase):
    """Tests for proxy capabilities."""

    def setUp(self):
        """Initial test setup."""
        super().setUp()
        # launch a mock server.
        command = ["pproxy", "-v", "-l", "http://{}:{}".format(ADDRESS, PORT)]
        self.proxy_process = subprocess.Popen(command, stdout=subprocess.PIPE)

    def tearDown(self):
        """Test cleanup."""
        super().tearDown()

        # terminate the mock server.
        if self.proxy_process.returncode is None:
            self.proxy_process.stdout.close()  # close the IO buffer
            self.proxy_process.terminate()  # initiate process termination

            # wait for the process to terminate
            self.proxy_process.wait()

    @integration_test_setup(supported_channel=["ibm_cloud"])
    def test_proxies_cloud_runtime_client(self, dependencies: IntegrationTestDependencies) -> None:
        """Should reach the proxy using RuntimeClient."""
        # pylint: disable=unused-argument
        params = dependencies.service._client_params
        params.proxies = ProxyConfiguration(urls=VALID_PROXIES)
        client = RuntimeClient(params)
        client.jobs_get(limit=1)
        api_line = pproxy_desired_access_log_line(params.url)
        self.proxy_process.terminate()  # kill to be able of reading the output
        proxy_output = self.proxy_process.stdout.read().decode("utf-8")
        self.assertIn(api_line, proxy_output)

    @integration_test_setup(supported_channel=["ibm_quantum"], init_service=False)
    def test_proxies_ibm_quantum_runtime_client(
        self, dependencies: IntegrationTestDependencies
    ) -> None:
        """Should reach the proxy using RuntimeClient."""
        service = QiskitRuntimeService(
            channel="ibm_quantum",
            token=dependencies.token,
            url=dependencies.url,
            proxies={"urls": VALID_PROXIES},
        )
        service.jobs(limit=1)

        auth_line = pproxy_desired_access_log_line(dependencies.url)
        api_line = list(service._hgps.values())[0]._runtime_client._session.base_url
        api_line = pproxy_desired_access_log_line(api_line)
        self.proxy_process.terminate()  # kill to be able of reading the output
        proxy_output = self.proxy_process.stdout.read().decode("utf-8")

        # Check if the authentication call went through proxy.
        self.assertIn(auth_line, proxy_output)
        # Check if the API call (querying providers list) went through proxy.
        self.assertIn(api_line, proxy_output)

    @integration_test_setup(supported_channel=["ibm_quantum"], init_service=False)
    def test_proxies_account_client(self, dependencies: IntegrationTestDependencies) -> None:
        """Should reach the proxy using AccountClient."""
        service = QiskitRuntimeService(
            channel="ibm_quantum",
            token=dependencies.token,
            url=dependencies.url,
            proxies={"urls": VALID_PROXIES},
        )

        self.proxy_process.terminate()  # kill to be able of reading the output

        auth_line = pproxy_desired_access_log_line(dependencies.url)
        api_line = list(service._hgps.values())[0]._runtime_client._session.base_url
        api_line = pproxy_desired_access_log_line(api_line)
        proxy_output = self.proxy_process.stdout.read().decode("utf-8")

        # Check if the authentication call went through proxy.
        self.assertIn(auth_line, proxy_output)
        # Check if the API call (querying providers list) went through proxy.
        self.assertIn(api_line, proxy_output)

    @integration_test_setup(supported_channel=["ibm_quantum"], init_service=False)
    def test_proxies_authclient(self, dependencies: IntegrationTestDependencies) -> None:
        """Should reach the proxy using AuthClient."""
        pproxy_desired_access_log_line_ = pproxy_desired_access_log_line(dependencies.url)
        params = ClientParameters(
            channel="ibm_quantum",
            token=dependencies.token,
            url=dependencies.url,
            proxies=ProxyConfiguration(urls=VALID_PROXIES),
        )

        _ = AuthClient(params)

        self.proxy_process.terminate()  # kill to be able of reading the output
        self.assertIn(
            pproxy_desired_access_log_line_,
            self.proxy_process.stdout.read().decode("utf-8"),
        )

    @integration_test_setup(supported_channel=["ibm_quantum"], init_service=False)
    def test_proxies_versionclient(self, dependencies: IntegrationTestDependencies) -> None:
        """Should reach the proxy using IBMVersionFinder."""
        pproxy_desired_access_log_line_ = pproxy_desired_access_log_line(dependencies.url)

        version_finder = VersionClient(dependencies.url, proxies=VALID_PROXIES)
        version_finder.version()

        self.proxy_process.terminate()  # kill to be able of reading the output
        self.assertIn(
            pproxy_desired_access_log_line_,
            self.proxy_process.stdout.read().decode("utf-8"),
        )

    @integration_test_setup(supported_channel=["ibm_quantum"], init_service=False)
    def test_invalid_proxy_port_runtime_client(
        self, dependencies: IntegrationTestDependencies
    ) -> None:
        """Should raise RequestApiError with ProxyError using RuntimeClient."""
        params = ClientParameters(
            channel="ibm_quantum",
            token=dependencies.token,
            url=dependencies.url,
            proxies=ProxyConfiguration(urls=INVALID_PORT_PROXIES),
        )
        with self.assertRaises(RequestsApiError) as context_manager:
            client = RuntimeClient(params)
            client.jobs_get(limit=1)
        self.assertIsInstance(context_manager.exception.__cause__, ProxyError)

    @integration_test_setup(supported_channel=["ibm_quantum"], init_service=False)
    def test_invalid_proxy_port_authclient(self, dependencies: IntegrationTestDependencies) -> None:
        """Should raise RequestApiError with ProxyError using AuthClient."""
        params = ClientParameters(
            channel="ibm_quantum",
            token=dependencies.token,
            url=dependencies.url,
            proxies=ProxyConfiguration(urls=INVALID_PORT_PROXIES),
        )
        with self.assertRaises(RequestsApiError) as context_manager:
            _ = AuthClient(params)

        self.assertIsInstance(context_manager.exception.__cause__, ProxyError)

    @integration_test_setup(supported_channel=["ibm_quantum"], init_service=False)
    def test_invalid_proxy_port_versionclient(
        self, dependencies: IntegrationTestDependencies
    ) -> None:
        """Should raise RequestApiError with ProxyError using VersionClient."""
        with self.assertRaises(RequestsApiError) as context_manager:
            version_finder = VersionClient(dependencies.url, proxies=INVALID_PORT_PROXIES)
            version_finder.version()

        self.assertIsInstance(context_manager.exception.__cause__, ProxyError)

    @integration_test_setup(supported_channel=["ibm_quantum"], init_service=False)
    def test_invalid_proxy_address_runtime_client(
        self, dependencies: IntegrationTestDependencies
    ) -> None:
        """Should raise RequestApiError with ProxyError using RuntimeClient."""
        params = ClientParameters(
            channel="ibm_quantum",
            token=dependencies.token,
            url=dependencies.url,
            proxies=ProxyConfiguration(urls=INVALID_ADDRESS_PROXIES),
        )
        with self.assertRaises(RequestsApiError) as context_manager:
            client = RuntimeClient(params)
            client.jobs_get(limit=1)

        self.assertIsInstance(context_manager.exception.__cause__, ProxyError)

    @integration_test_setup(supported_channel=["ibm_quantum"], init_service=False)
    def test_invalid_proxy_address_authclient(
        self, dependencies: IntegrationTestDependencies
    ) -> None:
        """Should raise RequestApiError with ProxyError using AuthClient."""
        params = ClientParameters(
            channel="ibm_quantum",
            token=dependencies.token,
            url=dependencies.url,
            proxies=ProxyConfiguration(urls=INVALID_ADDRESS_PROXIES),
        )
        with self.assertRaises(RequestsApiError) as context_manager:
            _ = AuthClient(params)

        self.assertIsInstance(context_manager.exception.__cause__, ProxyError)

    @integration_test_setup(supported_channel=["ibm_quantum"], init_service=False)
    def test_invalid_proxy_address_versionclient(
        self, dependencies: IntegrationTestDependencies
    ) -> None:
        """Should raise RequestApiError with ProxyError using VersionClient."""
        with self.assertRaises(RequestsApiError) as context_manager:
            version_finder = VersionClient(dependencies.url, proxies=INVALID_ADDRESS_PROXIES)
            version_finder.version()

        self.assertIsInstance(context_manager.exception.__cause__, ProxyError)

    @integration_test_setup(supported_channel=["ibm_quantum"], init_service=False)
    def test_proxy_urls(self, dependencies: IntegrationTestDependencies) -> None:
        """Test different forms of the proxy urls."""
        test_urls = [
            "http://{}:{}".format(ADDRESS, PORT),
            "//{}:{}".format(ADDRESS, PORT),
            "http://user:123@{}:{}".format(ADDRESS, PORT),
        ]
        for proxy_url in test_urls:
            with self.subTest(proxy_url=proxy_url):
                params = ClientParameters(
                    channel="ibm_quantum",
                    token=dependencies.token,
                    url=dependencies.url,
                    proxies=ProxyConfiguration(urls={"https": proxy_url}),
                )
                version_finder = VersionClient(params.url, **params.connection_parameters())
                version_finder.version()


def pproxy_desired_access_log_line(url):
    """Return a desired pproxy log entry given a url."""
    qe_url_parts = urllib.parse.urlparse(url)
    protocol_port = "443" if qe_url_parts.scheme == "https" else "80"
    return "{}:{}".format(qe_url_parts.hostname, protocol_port)
