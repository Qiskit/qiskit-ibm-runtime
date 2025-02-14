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

"""Tests for job functions using real runtime service."""


from qiskit_ibm_runtime.exceptions import RuntimeJobTimeoutError

from ..unit.mock.proxy_server import MockProxyServer, use_proxies
from ..ibm_test_case import IBMIntegrationJobTestCase
from ..decorators import run_integration_test


class TestIntegrationResults(IBMIntegrationJobTestCase):
    """Integration tests for result callbacks."""

    @run_integration_test
    def test_result_timeout(self, service):
        """Test job result timeout"""
        job = self._run_program(service)
        with self.assertRaises(RuntimeJobTimeoutError):
            job.result(0.1)

    @run_integration_test
    def test_wait_for_final_state_timeout(self, service):
        """Test job wait_for_final_state timeout"""
        job = self._run_program(service)
        with self.assertRaises(RuntimeJobTimeoutError):
            job.wait_for_final_state(0.1)

    @run_integration_test
    def test_websocket_proxy_invalid_port(self, service):
        """Test connecting to websocket via invalid proxy port."""

        def result_callback(job_id, result):  # pylint: disable=unused-argument
            nonlocal callback_called
            callback_called = True

        callback_called = False
        invalid_proxy = {
            "https": "http://{}:{}".format(
                MockProxyServer.PROXY_IP_ADDRESS, MockProxyServer.INVALID_PROXY_PORT
            )
        }
        # TODO - verify WebsocketError in output log. For some reason self.assertLogs
        # doesn't always work even when the error is clearly logged.
        with use_proxies(service, invalid_proxy):
            job = self._run_program(service, callback=result_callback)
            job.wait_for_final_state()
        self.assertFalse(callback_called)
