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

"""Tests for the proxy support."""

import subprocess
import urllib
from time import sleep
import socket


from qiskit_ibm_runtime import QiskitRuntimeService
from qiskit_ibm_runtime.proxies import ProxyConfiguration
from qiskit_ibm_runtime.accounts.exceptions import InvalidAccountError
from qiskit_ibm_runtime.api.client_parameters import ClientParameters
from qiskit_ibm_runtime.api.clients.runtime import RuntimeClient

from ..ibm_test_case import IBMTestCase
from ..decorators import IntegrationTestDependencies, integration_test_setup

ADDRESS = "127.0.0.1"
PORT = 8085
VALID_PROXIES = {"https": f"http://{ADDRESS}:{PORT}"}
INVALID_PORT_PROXIES = {"https": "http://{}:{}".format(ADDRESS, "6666")}
INVALID_ADDRESS_PROXIES = {"https": "http://{}:{}".format("invalid", PORT)}


class TestProxies(IBMTestCase):
    """Tests for proxy capabilities."""

    def setUp(self):
        """Initial test setup."""
        super().setUp()
        # launch a mock server.
        command = ["pproxy", "-v", "-l", f"http://{ADDRESS}:{PORT}"]
        self.proxy_process = subprocess.Popen(command, stdout=subprocess.PIPE)
        # Time for the proxy to start
        sleep(2)
        # Block all traffic not routed to the proxy
        self._original_connect = socket.socket.connect

        def blocking_connect(sock, address):
            if address != (ADDRESS, PORT):
                raise RuntimeError(f"Blocked network access to {address}")
            return self._original_connect(sock, address)

        socket.socket.connect = blocking_connect

    def tearDown(self):
        """Test cleanup."""
        super().tearDown()

        # terminate the mock server.
        if self.proxy_process.returncode is None:
            self.proxy_process.stdout.close()  # close the IO buffer
            self.proxy_process.terminate()  # initiate process termination

            # wait for the process to terminate
            self.proxy_process.wait()
        socket.socket.connect = self._original_connect

    @integration_test_setup(supported_channel=["ibm_quantum_platform"], init_service=False)
    def test_proxies_cloud_runtime_client(self, dependencies: IntegrationTestDependencies) -> None:
        """Should reach the proxy using RuntimeClient."""
        params = ClientParameters(
            instance=dependencies.instance,
            token=dependencies.token,
            channel=dependencies.channel,
            verify=False,
            proxies=ProxyConfiguration(urls=VALID_PROXIES),
            url=dependencies.url,
        )
        client = RuntimeClient(params)
        client.jobs_get(limit=1)
        api_line = pproxy_desired_access_log_line(params.url)
        self.proxy_process.terminate()  # kill to be able of reading the output
        proxy_output = self.proxy_process.stdout.read().decode("utf-8")
        self.assertIn(api_line, proxy_output)

    @integration_test_setup(supported_channel=["ibm_quantum_platform"], init_service=False)
    def test_proxies_qiskit_runtime_service(
        self, dependencies: IntegrationTestDependencies
    ) -> None:
        """Should reach the proxy using QiskitRuntimeService."""
        service = QiskitRuntimeService(
            instance=dependencies.instance,
            token=dependencies.token,
            channel=dependencies.channel,
            verify=False,
            proxies={"urls": VALID_PROXIES},
            url=dependencies.url,
        )
        service.jobs(limit=1)

        api_line = pproxy_desired_access_log_line(dependencies.url)
        self.proxy_process.terminate()  # kill to be able of reading the output
        proxy_output = self.proxy_process.stdout.read().decode("utf-8")
        self.assertIn(api_line, proxy_output)

    @integration_test_setup(supported_channel=["ibm_quantum_platform"], init_service=False)
    def test_no_proxy_raises_exception(self, dependencies: IntegrationTestDependencies) -> None:
        """Should raise an exception when no proxy is specified."""
        with self.assertRaises(InvalidAccountError):
            service = QiskitRuntimeService(
                instance=dependencies.instance,
                token=dependencies.token,
                channel=dependencies.channel,
            )
            service.jobs(limit=1)


def pproxy_desired_access_log_line(url):
    """Return a desired pproxy log entry given a url."""
    qe_url_parts = urllib.parse.urlparse(url)
    protocol_port = "443" if qe_url_parts.scheme == "https" else "80"
    return f"{qe_url_parts.hostname}:{protocol_port}"
