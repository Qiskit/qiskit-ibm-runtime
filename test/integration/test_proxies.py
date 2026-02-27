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


from qiskit_ibm_runtime.proxies import ProxyConfiguration
from qiskit_ibm_runtime.api.clients.runtime import RuntimeClient

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


def pproxy_desired_access_log_line(url):
    """Return a desired pproxy log entry given a url."""
    qe_url_parts = urllib.parse.urlparse(url)
    protocol_port = "443" if qe_url_parts.scheme == "https" else "80"
    return "{}:{}".format(qe_url_parts.hostname, protocol_port)
