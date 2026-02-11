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
import time

from qiskit_ibm_runtime.proxies import ProxyConfiguration
from qiskit_ibm_runtime.api.clients.runtime import RuntimeClient

from ..ibm_test_case import IBMTestCase
from ..decorators import IntegrationTestDependencies, integration_test_setup
from ..utils import find_free_port

ADDRESS = "127.0.0.1"
PORT = find_free_port()
VALID_PROXIES = {"https": "http://{}:{}".format(ADDRESS, PORT)}
INVALID_PORT_PROXIES = {"https": "http://{}:{}".format(ADDRESS, "6666")}
INVALID_ADDRESS_PROXIES = {"https": "http://{}:{}".format("invalid", PORT)}

class TestProxies(IBMTestCase):
    """Tests for proxy capabilities."""

    def setUp(self):
        # Pick a random free port for mitmproxy
        super().setUp()
        # Command to start mitmproxy in non-interactive mode
        self.proc = subprocess.Popen(
            [
                "mitmdump",
                "--listen-port",
                str(PORT),
                "--listen-host",
                ADDRESS
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        time.sleep(0.5)


    def tearDown(self):
        super().tearDown()
        # Kill the proxy process
        if self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=1)
            except subprocess.TimeoutExpired:
                self.proc.kill()

    @integration_test_setup(supported_channel=["ibm_cloud", "ibm_quantum_platform"])
    def test_proxies_cloud_runtime_client(self, dependencies: IntegrationTestDependencies) -> None:
        """Should reach the proxy using RuntimeClient."""
        # pylint: disable=unused-argument
        params = dependencies.service._client_params
        params.proxies = ProxyConfiguration(urls=VALID_PROXIES)
        params.verify = False
        client = RuntimeClient(params)
        client.jobs_get(limit=1)
        self.assertTrue(True)