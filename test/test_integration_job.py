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

import copy
import unittest
import uuid
import time
import random
from contextlib import suppress
from collections import defaultdict

from qiskit.providers.jobstatus import JobStatus, JOB_FINAL_STATES
from qiskit.providers.exceptions import QiskitBackendNotFoundError
from qiskit.test.decorators import slow_test

from qiskit_ibm_runtime.constants import API_TO_JOB_ERROR_MESSAGE
from qiskit_ibm_runtime.exceptions import IBMNotAuthorizedError
from qiskit_ibm_runtime.exceptions import (
    RuntimeDuplicateProgramError,
    RuntimeJobFailureError,
    RuntimeInvalidStateError,
    RuntimeJobNotFound,
)

from .ibm_test_case import IBMTestCase
from .utils.decorators import requires_cloud_legacy_services, run_cloud_legacy_real
from .utils.templates import RUNTIME_PROGRAM, RUNTIME_PROGRAM_METADATA, PROGRAM_PREFIX
from .utils.serialization import (
    get_complex_types,
    SerializableClassDecoder,
    SerializableClass,
)
from .mock.proxy_server import MockProxyServer, use_proxies


class TestIntegrationJob(IBMTestCase):
    """Integration tests for job functions."""

    @classmethod
    @requires_cloud_legacy_services
    def setUpClass(cls, services):
        """Initial class level setup."""
        # pylint: disable=arguments-differ
        super().setUpClass()
        cls.services = services
        metadata = copy.deepcopy(RUNTIME_PROGRAM_METADATA)
        metadata["name"] = cls._get_program_name()
        cls.program_ids = {}
        cls.sim_backends = {}
        cls.real_backends = {}
        for service in services:
            try:
                prog_id = service.upload_program(
                    data=RUNTIME_PROGRAM, metadata=metadata
                )
                cls.log.debug("Uploaded %s program %s", service.auth, prog_id)
                cls.program_ids[service.auth] = prog_id
            except RuntimeDuplicateProgramError:
                pass
            except IBMNotAuthorizedError:
                raise unittest.SkipTest("No upload access.")

            cls.sim_backends[service.auth] = service.backends(simulator=True)[0].name()

    @classmethod
    def tearDownClass(cls) -> None:
        """Class level teardown."""
        super().tearDownClass()
        with suppress(Exception):
            for service in cls.services:
                service.delete_program(cls.program_ids[service.auth])
                cls.log.debug(
                    "Deleted %s program %s", service.auth, cls.program_ids[service.auth]
                )

    def setUp(self) -> None:
        """Test level setup."""
        super().setUp()
        self.poll_time = 1
        self.to_delete = defaultdict(list)
        self.to_cancel = defaultdict(list)

    def tearDown(self) -> None:
        """Test level teardown."""
        super().tearDown()
        # Delete programs
        for service in self.services:
            for prog in self.to_delete[service.auth]:
                with suppress(Exception):
                    service.delete_program(prog)

        # Cancel and delete jobs.
        for service in self.services:
            for job in self.to_cancel[service.auth]:
                with suppress(Exception):
                    job.cancel()
                with suppress(Exception):
                    service.delete_job(job.job_id)

    @run_cloud_legacy_real
    def test_run_program(self, service):
        """Test running a program."""
        job = self._run_program(service, final_result="foo")
        result = job.result()
        self.assertEqual(JobStatus.DONE, job.status())
        self.assertEqual("foo", result)

    @slow_test
    @run_cloud_legacy_real
    def test_run_program_real_device(self, service):
        """Test running a program."""
        device = self._get_real_device(service)
        job = self._run_program(service, final_result="foo", backend=device)
        result = job.result()
        self.assertEqual(JobStatus.DONE, job.status())
        self.assertEqual("foo", result)

    @run_cloud_legacy_real
    def test_run_program_failed(self, service):
        """Test a failed program execution."""
        job = self._run_program(service, inputs={})
        job.wait_for_final_state()
        job_result_raw = service._api_client.job_results(job.job_id)
        self.assertEqual(JobStatus.ERROR, job.status())
        self.assertIn(
            API_TO_JOB_ERROR_MESSAGE["FAILED"].format(job.job_id, job_result_raw),
            job.error_message(),
        )
        with self.assertRaises(RuntimeJobFailureError) as err_cm:
            job.result()
        self.assertIn("KeyError", str(err_cm.exception))

    @run_cloud_legacy_real
    def test_run_program_failed_ran_too_long(self, service):
        """Test a program that failed since it ran longer than maximum execution time."""
        max_execution_time = 60
        inputs = {"iterations": 1, "sleep_per_iteration": 60}
        program_id = self._upload_program(
            service, max_execution_time=max_execution_time
        )
        job = self._run_program(service, program_id=program_id, inputs=inputs)

        job.wait_for_final_state()
        job_result_raw = service._api_client.job_results(job.job_id)
        self.assertEqual(JobStatus.ERROR, job.status())
        self.assertIn(
            API_TO_JOB_ERROR_MESSAGE["CANCELLED - RAN TOO LONG"].format(
                job.job_id, job_result_raw
            ),
            job.error_message(),
        )
        with self.assertRaises(RuntimeJobFailureError):
            job.result()

    @run_cloud_legacy_real
    def test_retrieve_job_queued(self, service):
        """Test retrieving a queued job."""
        real_device = self._get_real_device(service)
        _ = self._run_program(service, iterations=10, backend=real_device)
        job = self._run_program(service, iterations=2, backend=real_device)
        self._wait_for_status(job, JobStatus.QUEUED)
        rjob = service.job(job.job_id)
        self.assertEqual(job.job_id, rjob.job_id)
        self.assertEqual(self.program_ids[service.auth], rjob.program_id)

    @run_cloud_legacy_real
    def test_retrieve_job_running(self, service):
        """Test retrieving a running job."""
        job = self._run_program(service, iterations=10)
        self._wait_for_status(job, JobStatus.RUNNING)
        rjob = service.job(job.job_id)
        self.assertEqual(job.job_id, rjob.job_id)
        self.assertEqual(self.program_ids[service.auth], rjob.program_id)

    @run_cloud_legacy_real
    def test_retrieve_job_done(self, service):
        """Test retrieving a finished job."""
        job = self._run_program(service)
        job.wait_for_final_state()
        rjob = service.job(job.job_id)
        self.assertEqual(job.job_id, rjob.job_id)
        self.assertEqual(self.program_ids[service.auth], rjob.program_id)

    @run_cloud_legacy_real
    def test_retrieve_all_jobs(self, service):
        """Test retrieving all jobs."""
        job = self._run_program(service)
        rjobs = service.jobs()
        found = False
        for rjob in rjobs:
            if rjob.job_id == job.job_id:
                self.assertEqual(job.program_id, rjob.program_id)
                self.assertEqual(job.inputs, rjob.inputs)
                found = True
                break
        self.assertTrue(found, f"Job {job.job_id} not returned.")

    @run_cloud_legacy_real
    def test_retrieve_jobs_limit(self, service):
        """Test retrieving jobs with limit."""
        jobs = []
        for _ in range(3):
            jobs.append(self._run_program(service))

        rjobs = service.jobs(limit=2, program_id=self.program_ids[service.auth])
        self.assertEqual(len(rjobs), 2)
        job_ids = {job.job_id for job in jobs}
        rjob_ids = {rjob.job_id for rjob in rjobs}
        self.assertTrue(
            rjob_ids.issubset(job_ids), f"Submitted: {job_ids}, Retrieved: {rjob_ids}"
        )

    @run_cloud_legacy_real
    def test_retrieve_pending_jobs(self, service):
        """Test retrieving pending jobs (QUEUED, RUNNING)."""
        job = self._run_program(service, iterations=10)
        self._wait_for_status(job, JobStatus.RUNNING)
        rjobs = service.jobs(pending=True)
        found = False
        for rjob in rjobs:
            if rjob.job_id == job.job_id:
                self.assertEqual(job.program_id, rjob.program_id)
                self.assertEqual(job.inputs, rjob.inputs)
                found = True
                break
        self.assertTrue(found, f"Pending job {job.job_id} not retrieved.")

    @run_cloud_legacy_real
    def test_retrieve_returned_jobs(self, service):
        """Test retrieving returned jobs (COMPLETED, FAILED, CANCELLED)."""
        job = self._run_program(service)
        job.wait_for_final_state()
        rjobs = service.jobs(pending=False)
        found = False
        for rjob in rjobs:
            if rjob.job_id == job.job_id:
                self.assertEqual(job.program_id, rjob.program_id)
                self.assertEqual(job.inputs, rjob.inputs)
                found = True
                break
        self.assertTrue(found, f"Returned job {job.job_id} not retrieved.")

    @run_cloud_legacy_real
    def test_retrieve_jobs_by_program_id(self, service):
        """Test retrieving jobs by Program ID."""
        program_id = self._upload_program(service)
        job = self._run_program(service, program_id=program_id)
        job.wait_for_final_state()
        rjobs = service.jobs(program_id=program_id)
        self.assertEqual(program_id, rjobs[0].program_id)
        self.assertEqual(1, len(rjobs))

    def test_jobs_filter_by_hgp(self):
        """Test retrieving jobs by hgp."""
        service = [serv for serv in self.services if serv.auth == "legacy"][0]
        default_hgp = list(service._hgps.keys())[0]
        program_id = self._upload_program(service)
        job = self._run_program(service, program_id=program_id)
        job.wait_for_final_state()
        rjobs = service.jobs(program_id=program_id, instance=default_hgp)
        self.assertEqual(program_id, rjobs[0].program_id)
        self.assertEqual(1, len(rjobs))

        uuid_ = uuid.uuid4().hex
        fake_hgp = f"{uuid_}/{uuid_}/{uuid_}"
        rjobs = service.jobs(program_id=program_id, instance=fake_hgp)
        self.assertFalse(rjobs)

    @run_cloud_legacy_real
    def test_cancel_job_queued(self, service):
        """Test canceling a queued job."""
        real_device = self._get_real_device(service)
        _ = self._run_program(service, iterations=10, backend=real_device)
        job = self._run_program(service, iterations=2, backend=real_device)
        self._wait_for_status(job, JobStatus.QUEUED)
        job.cancel()
        self.assertEqual(job.status(), JobStatus.CANCELLED)
        time.sleep(10)  # Wait a bit for DB to update.
        rjob = service.job(job.job_id)
        self.assertEqual(rjob.status(), JobStatus.CANCELLED)

    @run_cloud_legacy_real
    def test_cancel_job_running(self, service):
        """Test canceling a running job."""
        job = self._run_program(service, iterations=3)
        self._wait_for_status(job, JobStatus.RUNNING)
        job.cancel()
        self.assertEqual(job.status(), JobStatus.CANCELLED)
        time.sleep(10)  # Wait a bit for DB to update.
        rjob = service.job(job.job_id)
        self.assertEqual(rjob.status(), JobStatus.CANCELLED)

    @run_cloud_legacy_real
    def test_cancel_job_done(self, service):
        """Test canceling a finished job."""
        job = self._run_program(service)
        job.wait_for_final_state()
        with self.assertRaises(RuntimeInvalidStateError):
            job.cancel()

    @run_cloud_legacy_real
    def test_delete_job(self, service):
        """Test deleting a job."""
        sub_tests = [JobStatus.RUNNING, JobStatus.DONE]
        for status in sub_tests:
            with self.subTest(status=status):
                job = self._run_program(service, iterations=2)
                self._wait_for_status(job, status)
                service.delete_job(job.job_id)
                with self.assertRaises(RuntimeJobNotFound):
                    service.job(job.job_id)

    @run_cloud_legacy_real
    def test_delete_job_queued(self, service):
        """Test deleting a queued job."""
        real_device = self._get_real_device(service)
        _ = self._run_program(service, iterations=10, backend=real_device)
        job = self._run_program(service, iterations=2, backend=real_device)
        self._wait_for_status(job, JobStatus.QUEUED)
        service.delete_job(job.job_id)
        with self.assertRaises(RuntimeJobNotFound):
            service.job(job.job_id)

    @run_cloud_legacy_real
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

    @run_cloud_legacy_real
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

    @run_cloud_legacy_real
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

    @run_cloud_legacy_real
    def test_retrieve_interim_results(self, service):
        """Test retrieving interim results with API endpoint"""
        int_res = "foo"
        job = self._run_program(service, interim_results=int_res)
        job.wait_for_final_state()
        interim_results = job.interim_results()
        self.assertIn(int_res, interim_results[0])

    @run_cloud_legacy_real
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

    @run_cloud_legacy_real
    def test_callback_cancel_job(self, service):
        """Test canceling a running job while streaming results."""

        def result_callback(job_id, interim_result):
            # pylint: disable=unused-argument
            nonlocal final_it
            final_it = interim_result["iteration"]

        final_it = 0
        iterations = 3
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
                self._wait_for_status(job, status)
                job.cancel()
                time.sleep(3)  # Wait for cleanup
                self.assertIsNotNone(job._ws_client._server_close_code)
                self.assertLess(final_it, iterations)

    @run_cloud_legacy_real
    def test_final_result(self, service):
        """Test getting final result."""
        final_result = get_complex_types()
        job = self._run_program(service, final_result=final_result)
        result = job.result(decoder=SerializableClassDecoder)
        self.assertEqual(final_result, result)

        rresults = service.job(job.job_id).result(decoder=SerializableClassDecoder)
        self.assertEqual(final_result, rresults)

    @run_cloud_legacy_real
    def test_job_status(self, service):
        """Test job status."""
        job = self._run_program(service, iterations=1)
        time.sleep(random.randint(1, 5))
        self.assertTrue(job.status())

    @run_cloud_legacy_real
    def test_job_inputs(self, service):
        """Test job inputs."""
        interim_results = get_complex_types()
        inputs = {"iterations": 1, "interim_results": interim_results}
        job = self._run_program(service, inputs=inputs)
        self.assertEqual(inputs, job.inputs)
        rjob = service.job(job.job_id)
        rinterim_results = rjob.inputs["interim_results"]
        self._assert_complex_types_equal(interim_results, rinterim_results)

    @run_cloud_legacy_real
    def test_job_backend(self, service):
        """Test job backend."""
        job = self._run_program(service)
        self.assertEqual(self.sim_backends[service.auth], job.backend.name())

    @run_cloud_legacy_real
    def test_job_program_id(self, service):
        """Test job program ID."""
        job = self._run_program(service)
        self.assertEqual(self.program_ids[service.auth], job.program_id)

    @run_cloud_legacy_real
    def test_wait_for_final_state(self, service):
        """Test wait for final state."""
        job = self._run_program(service)
        job.wait_for_final_state()
        self.assertEqual(JobStatus.DONE, job.status())

    @run_cloud_legacy_real
    def test_logout(self, service):
        """Test logout."""
        if service.auth == "cloud":
            # TODO - re-enable when fixed
            self.skipTest("Logout does not work for cloud")
        service.logout()
        # Make sure we can still do things.
        self._upload_program(service)
        _ = self._run_program(service)

    @run_cloud_legacy_real
    def test_job_creation_date(self, service):
        """Test job creation date."""
        job = self._run_program(service, iterations=1)
        self.assertTrue(job.creation_date)
        rjob = service.job(job.job_id)
        self.assertTrue(rjob.creation_date)
        rjobs = service.jobs(limit=2)
        for rjob in rjobs:
            self.assertTrue(rjob.creation_date)

    @run_cloud_legacy_real
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

    @run_cloud_legacy_real
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

    @run_cloud_legacy_real
    def test_job_logs(self, service):
        """Test job logs."""
        job = self._run_program(service, final_result="foo")
        with self.assertLogs("qiskit_ibm_runtime", "WARN"):
            job.logs()
        job.wait_for_final_state()
        job_logs = job.logs()
        self.assertIn("this is a stdout message", job_logs)
        self.assertIn("this is a stderr message", job_logs)

    def _upload_program(
        self,
        service,
        name=None,
        max_execution_time=300,
        data=None,
        is_public: bool = False,
    ):
        """Upload a new program."""
        name = name or self._get_program_name()
        data = data or RUNTIME_PROGRAM
        metadata = copy.deepcopy(RUNTIME_PROGRAM_METADATA)
        metadata["name"] = name
        metadata["max_execution_time"] = max_execution_time
        metadata["is_public"] = is_public
        program_id = service.upload_program(data=data, metadata=metadata)
        self.to_delete[service.auth].append(program_id)
        return program_id

    @classmethod
    def _get_program_name(cls):
        """Return a unique program name."""
        return PROGRAM_PREFIX + "_" + uuid.uuid4().hex

    def _assert_complex_types_equal(self, expected, received):
        """Verify the received data in complex types is expected."""
        if "serializable_class" in received:
            received["serializable_class"] = SerializableClass.from_json(
                received["serializable_class"]
            )
        self.assertEqual(expected, received)

    def _run_program(
        self,
        service,
        program_id=None,
        iterations=1,
        inputs=None,
        interim_results=None,
        final_result=None,
        callback=None,
        backend=None,
    ):
        """Run a program."""
        self.log.debug("Running program on %s", service.auth)
        inputs = (
            inputs
            if inputs is not None
            else {
                "iterations": iterations,
                "interim_results": interim_results or {},
                "final_result": final_result or {},
            }
        )
        pid = program_id or self.program_ids[service.auth]
        backend_name = backend or self.sim_backends[service.auth]
        options = {"backend_name": backend_name}
        job = service.run(
            program_id=pid, inputs=inputs, options=options, callback=callback
        )
        self.log.info("Runtime job %s submitted.", job.job_id)
        self.to_cancel[service.auth].append(job)
        return job

    def _wait_for_status(self, job, status):
        """Wait for job to reach a certain status."""
        wait_time = 1 if status == JobStatus.QUEUED else self.poll_time
        while job.status() not in JOB_FINAL_STATES + (status,):
            time.sleep(wait_time)
        if job.status() != status:
            self.skipTest(f"Job {job.job_id} unable to reach status {status}.")

    def _get_real_device(self, service):
        try:
            # TODO: Remove filters when ibmq_berlin is removed
            return service.least_busy(
                simulator=False, filters=lambda b: b.name() != "ibmq_berlin"
            ).name()
        except QiskitBackendNotFoundError:
            raise unittest.SkipTest("No real device")  # cloud has no real device
