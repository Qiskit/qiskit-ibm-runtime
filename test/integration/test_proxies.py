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

from __future__ import annotations

import socket
import subprocess
import urllib
from contextlib import contextmanager
from time import sleep
from typing import TYPE_CHECKING
from unittest.mock import patch

from qiskit_ibm_runtime import QiskitRuntimeService
from qiskit_ibm_runtime.accounts.exceptions import InvalidAccountError
from qiskit_ibm_runtime.api.client import RuntimeClient
from qiskit_ibm_runtime.api.client_parameters import ClientParameters
from qiskit_ibm_runtime.proxies import ProxyConfiguration

from ..ibm_test_case import IBMTestCase
from .case import integration_test_dependencies

if TYPE_CHECKING:
    from collections.abc import Iterator

ADDRESS = "127.0.0.1"
PORT = 8085
VALID_PROXIES = {"https": f"http://{ADDRESS}:{PORT}"}
INVALID_PORT_PROXIES = {"https": "http://{}:{}".format(ADDRESS, "6666")}
INVALID_ADDRESS_PROXIES = {"https": "http://{}:{}".format("invalid", PORT)}


@contextmanager
def blocked_network() -> Iterator[None]:
    """Block the network traffic that is not routed to the proxy, restoring it on exit."""
    original_connect = socket.socket.connect

    def blocking_connect(sock: socket.socket, address: tuple) -> None:
        if address != (ADDRESS, PORT):
            raise RuntimeError(f"Blocked network access to {address}")
        return original_connect(sock, address)

    with patch.object(socket.socket, "connect", blocking_connect):
        yield


@contextmanager
def proxy_server() -> Iterator[subprocess.Popen]:
    """Run a `pproxy` server, blocking the network traffic that is not routed to it.

    Yields:
        The process running the server. A test can terminate it early to read its output.
    """
    command = ["pproxy", "-v", "-l", f"http://{ADDRESS}:{PORT}"]
    process = subprocess.Popen(command, stdout=subprocess.PIPE)  # noqa: S603
    sleep(2)  # give the server time to start

    try:
        with blocked_network():
            yield process
    finally:
        if process.returncode is None:
            process.stdout.close()  # close the IO buffer
            process.terminate()
            process.wait()


class TestProxies(IBMTestCase):
    """Tests for proxy capabilities."""

    def test_proxies_cloud_runtime_client(self) -> None:
        """Should reach the proxy using RuntimeClient."""
        dependencies = integration_test_dependencies(init_service=False)

        with proxy_server() as process:
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
            process.terminate()  # kill to be able of reading the output
            proxy_output = process.stdout.read().decode("utf-8")

        assert api_line in proxy_output

    def test_proxies_qiskit_runtime_service(self) -> None:
        """Should reach the proxy using QiskitRuntimeService."""
        dependencies = integration_test_dependencies(init_service=False)

        with proxy_server() as process:
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
            process.terminate()  # kill to be able of reading the output
            proxy_output = process.stdout.read().decode("utf-8")

        assert api_line in proxy_output

    def test_no_proxy_raises_exception(self) -> None:
        """Should raise an exception when no proxy is specified."""
        dependencies = integration_test_dependencies(init_service=False)

        with proxy_server(), self.assertRaises(InvalidAccountError):
            service = QiskitRuntimeService(
                instance=dependencies.instance,
                token=dependencies.token,
                channel=dependencies.channel,
            )
            service.jobs(limit=1)


def pproxy_desired_access_log_line(url: str) -> str:
    """Return a desired pproxy log entry given a url."""
    qe_url_parts = urllib.parse.urlparse(url)
    protocol_port = "443" if qe_url_parts.scheme == "https" else "80"
    return f"{qe_url_parts.hostname}:{protocol_port}"
