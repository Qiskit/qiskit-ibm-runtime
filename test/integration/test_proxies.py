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

import asyncio
import socket
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING
from urllib.parse import urlparse

import pytest
from mitmproxy.options import Options
from mitmproxy.tools.dump import DumpMaster

from qiskit_ibm_runtime import QiskitRuntimeService
from qiskit_ibm_runtime.accounts.exceptions import InvalidAccountError
from qiskit_ibm_runtime.api.client import RuntimeClient
from qiskit_ibm_runtime.api.client_parameters import ClientParameters
from qiskit_ibm_runtime.proxies import ProxyConfiguration

from .dependencies import integration_test_dependencies

if TYPE_CHECKING:
    from collections.abc import Iterator

    from mitmproxy import http

ADDRESS = "127.0.0.1"


class RequestRecorder:
    """A mitmproxy addon that records the host and port of every proxied request."""

    def __init__(self) -> None:
        self.requests: list[tuple[str, int]] = []

    def request(self, flow: http.HTTPFlow) -> None:
        """Called by mitmproxy for each request it proxies."""
        self.requests.append((flow.request.pretty_host, flow.request.port))


@contextmanager
def blocked_network(
    *, allowed_address: tuple[str, int], exempt_thread_ident: int
) -> Iterator[None]:
    """Block the network traffic that is not routed to the proxy, restoring it on exit.

    Args:
        allowed_address: the only (host, port) the current thread may connect to directly.
        exempt_thread_ident: thread allowed to bypass the block entirely. The in-process
            mitmproxy server runs on its own thread in this same process, so without this
            exemption its own upstream connections would be blocked too, since the patch
            below is process-wide rather than scoped to the test's client code.
    """
    original_connect = socket.socket.connect

    def blocking_connect(sock: socket.socket, address: tuple) -> None:
        if address != allowed_address and threading.current_thread().ident != exempt_thread_ident:
            raise RuntimeError(f"Blocked network access to {address}")
        return original_connect(sock, address)

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(socket.socket, "connect", blocking_connect)
        yield


class _ReadySignal:
    """A mitmproxy addon that signals once the proxy's listener is actually up."""

    def __init__(self) -> None:
        self.ready = threading.Event()

    def running(self) -> None:
        """Called by mitmproxy once the server has finished starting up."""
        self.ready.set()


@dataclass
class ProxyServerHandle:
    """A handle to a running in-process mitmproxy server."""

    recorder: RequestRecorder
    url: str


@contextmanager
def proxy_server() -> Iterator[ProxyServerHandle]:
    """Run an in-process mitmproxy server, blocking network traffic that is not routed to it.

    The listen port is chosen by the OS rather than fixed, so that repeated invocations
    within the same test run never race against the previous instance's port still being
    held by the kernel.

    Yields:
        A handle exposing the recorder and the proxy's actual URL.
    """
    recorder = RequestRecorder()
    ready_signal = _ReadySignal()
    master_holder: list[DumpMaster] = []
    startup_errors: list[BaseException] = []

    async def run_master() -> None:
        # DumpMaster needs a running event loop to be constructed, so it must be
        # built here, inside the background thread, rather than before it starts.
        options = Options(listen_host=ADDRESS, listen_port=0)
        master = DumpMaster(options, with_termlog=False, with_dumper=False)
        master.addons.add(recorder, ready_signal)  # type: ignore[no-untyped-call]
        master_holder.append(master)
        await master.run()

    def run_in_background() -> None:
        try:
            asyncio.run(run_master())
        except BaseException as exc:  # noqa: BLE001 -- surfaced to the main thread below
            startup_errors.append(exc)
            ready_signal.ready.set()  # unblock the waiter so the error can be raised

    thread = threading.Thread(target=run_in_background, daemon=True)
    thread.start()
    assert thread.ident is not None  # set as soon as start() returns

    if not ready_signal.ready.wait(timeout=10):
        raise RuntimeError("mitmproxy did not start within 10 seconds")
    if startup_errors:
        raise RuntimeError("mitmproxy failed to start") from startup_errors[0]

    master = master_holder[0]
    proxyserver = master.addons.get("proxyserver")  # type: ignore[no-untyped-call]
    assert proxyserver is not None
    bound_host, bound_port = proxyserver.listen_addrs()[0]

    try:
        with blocked_network(
            allowed_address=(bound_host, bound_port), exempt_thread_ident=thread.ident
        ):
            yield ProxyServerHandle(recorder=recorder, url=f"http://{bound_host}:{bound_port}")
    finally:
        master.shutdown()  # type: ignore[no-untyped-call]
        thread.join()


class TestProxies:
    """Tests for proxy capabilities."""

    def test_proxies_cloud_runtime_client(self) -> None:
        """Should reach the proxy using RuntimeClient."""
        dependencies = integration_test_dependencies(init_service=False)
        assert dependencies.channel is not None

        with proxy_server() as proxy:
            params = ClientParameters(
                instance=dependencies.instance,
                token=dependencies.token,
                channel=dependencies.channel,
                verify=False,
                proxies=ProxyConfiguration(urls={"https": proxy.url}),
                url=dependencies.url,
            )
            client = RuntimeClient(params)
            client.jobs_get(limit=1)

        assert proxied_request_matches_domain(proxy.recorder.requests, params.url)

    def test_proxies_qiskit_runtime_service(self) -> None:
        """Should reach the proxy using QiskitRuntimeService."""
        dependencies = integration_test_dependencies(init_service=False)

        with proxy_server() as proxy:
            service = QiskitRuntimeService(
                instance=dependencies.instance,
                token=dependencies.token,
                channel=dependencies.channel,
                verify=False,
                proxies={"urls": {"https": proxy.url}},
                url=dependencies.url,
            )
            service.jobs(limit=1)

        assert proxied_request_matches_domain(proxy.recorder.requests, dependencies.url)

    def test_no_proxy_raises_exception(self) -> None:
        """Should raise an exception when no proxy is specified."""
        dependencies = integration_test_dependencies(init_service=False)

        with proxy_server(), pytest.raises(InvalidAccountError):
            service = QiskitRuntimeService(
                instance=dependencies.instance,
                token=dependencies.token,
                channel=dependencies.channel,
            )
            service.jobs(limit=1)


def proxied_request_matches_domain(requests: list[tuple[str, int]], url: str | None) -> bool:
    """Check that at least one proxied request was made under `url`'s domain.

    The `ibm_quantum_platform` channel never requests `url` itself: it fans out across
    several subdomains (IAM auth, the quantum runtime API, global catalog/search for CRN
    resolution), all living under `url`'s own domain. That shared domain is the strongest
    invariant available, since the exact subdomain touched can change as the SDK's internal
    request flow evolves.
    """
    domain = urlparse(url).hostname if url else None
    return domain is not None and any(
        host == domain or host.endswith(f".{domain}") for host, _ in requests
    )
