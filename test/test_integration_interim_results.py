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

import time

from qiskit.providers.jobstatus import JobStatus

from .ibm_test_case import IBMIntegrationJobTestCase
from .utils.decorators import run_integration_test
from .utils.utils import cancel_job_safe, wait_for_status
from .mock.proxy_server import MockProxyServer, use_proxies


class TestIntegrationInterimResults(IBMIntegrationJobTestCase):
    """Integration tests for interim result functions."""

    @run_integration_test
    def test_interim_result_callback(self, service):
        """Test interim result callback."""

        def result_callback(job_id, interim_result):
            nonlocal final_it
            final_it = interim_result["iteration"]
            nonlocal callback_err
            if job_id != job.job_id:
                callback_err.append(f"Unexpected job ID: {job_id}")
            if interim_result["interim_results"] != int_res:
                callback_err.append(f"Unexpected interim result: {interim_result}")

        int_res = "foo"
        final_it = 0
        callback_err = []
        iterations = 3
        job = self._run_program(
            service,
            iterations=iterations,
            interim_results=int_res,
            callback=result_callback,
        )
        job.wait_for_final_state()
        self.assertEqual(iterations - 1, final_it)
        self.assertFalse(callback_err)
        self.assertIsNotNone(job._ws_client._server_close_code)

    @run_integration_test
    def test_stream_results(self, service):
        """Test stream_results method."""

        def result_callback(job_id, interim_result):
            nonlocal final_it
            final_it = interim_result["iteration"]
            nonlocal callback_err
            if job_id != job.job_id:
                callback_err.append(f"Unexpected job ID: {job_id}")
            if interim_result["interim_results"] != int_res:
                callback_err.append(f"Unexpected interim result: {interim_result}")

        int_res = "bar"
        final_it = 0
        callback_err = []
        iterations = 3
        job = self._run_program(service, iterations=iterations, interim_results=int_res)
        job.stream_results(result_callback)
        job.wait_for_final_state()
        self.assertEqual(iterations - 1, final_it)
        self.assertFalse(callback_err)
        self.assertIsNotNone(job._ws_client._server_close_code)

    @run_integration_test
    def test_stream_results_done(self, service):
        """Test streaming interim results after job is done."""

        def result_callback(job_id, interim_result):
            # pylint: disable=unused-argument
            nonlocal called_back
            called_back = True

        called_back = False
        job = self._run_program(service, interim_results="foobar")
        job.wait_for_final_state()
        job._status = JobStatus.RUNNING  # Allow stream_results()
        job.stream_results(result_callback)
        time.sleep(2)
        self.assertFalse(called_back)
        self.assertIsNotNone(job._ws_client._server_close_code)

    @run_integration_test
    def test_retrieve_interim_results(self, service):
        """Test retrieving interim results with API endpoint"""
        int_res = "foo"
        job = self._run_program(service, interim_results=int_res)
        job.wait_for_final_state()
        interim_results = job.interim_results()
        self.assertIn(int_res, interim_results[0])

    @run_integration_test
    def test_callback_error(self, service):
        """Test error in callback method."""

        def result_callback(job_id, interim_result):
            # pylint: disable=unused-argument
            if interim_result["iteration"] == 0:
                raise ValueError("Kaboom!")
            nonlocal final_it
            final_it = interim_result["iteration"]

        final_it = 0
        iterations = 3
        with self.assertLogs("qiskit_ibm_runtime", level="WARNING") as err_cm:
            job = self._run_program(
                service,
                iterations=iterations,
                interim_results="foo",
                callback=result_callback,
            )
            job.wait_for_final_state()

        self.assertIn("Kaboom", ", ".join(err_cm.output))
        self.assertEqual(iterations - 1, final_it)
        self.assertIsNotNone(job._ws_client._server_close_code)

    @run_integration_test
    def test_callback_cancel_job(self, service):
        """Test canceling a running job while streaming results."""

        def result_callback(job_id, interim_result):
            # pylint: disable=unused-argument
            nonlocal final_it
            final_it = interim_result["iteration"]

        final_it = 0
        iterations = 5
        sub_tests = [JobStatus.QUEUED, JobStatus.RUNNING]

        for status in sub_tests:
            with self.subTest(status=status):
                if status == JobStatus.QUEUED:
                    _ = self._run_program(service, iterations=10)

                job = self._run_program(
                    service=service,
                    iterations=iterations,
                    interim_results="foo",
                    callback=result_callback,
                )
                wait_for_status(job, status)
                if not cancel_job_safe(job, self.log):
                    return
                time.sleep(3)  # Wait for cleanup
                self.assertIsNotNone(job._ws_client._server_close_code)
                self.assertLess(final_it, iterations)

    @run_integration_test
    def test_websocket_proxy(self, service):
        """Test connecting to websocket via proxy."""

        def result_callback(job_id, interim_result):  # pylint: disable=unused-argument
            nonlocal callback_called
            callback_called = True

        MockProxyServer(self, self.log).start()
        callback_called = False

        with use_proxies(service, MockProxyServer.VALID_PROXIES):
            job = self._run_program(service, iterations=1, callback=result_callback)
            job.wait_for_final_state()

        self.assertTrue(callback_called)

    @run_integration_test
    def test_websocket_proxy_invalid_port(self, service):
        """Test connecting to websocket via invalid proxy port."""

        def result_callback(job_id, interim_result):  # pylint: disable=unused-argument
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
            job = self._run_program(service, iterations=2, callback=result_callback)
            job.wait_for_final_state()
        self.assertFalse(callback_called)
