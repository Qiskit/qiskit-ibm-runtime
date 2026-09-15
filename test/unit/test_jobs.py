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

"""Tests for job related runtime functions."""

from __future__ import annotations

import json
import warnings
from typing import TYPE_CHECKING
from unittest.mock import patch

from ddt import data, ddt
from qiskit.providers.exceptions import QiskitBackendNotFoundError

from qiskit_ibm_runtime import RuntimeJobV2
from qiskit_ibm_runtime.base_runtime_job import API_TO_JOB_ERROR_MESSAGE
from qiskit_ibm_runtime.decoders.result_decoder import ResultDecoder
from qiskit_ibm_runtime.exceptions import (
    RuntimeInvalidStateError,
    RuntimeJobFailureError,
    RuntimeJobMaxTimeoutError,
    RuntimeJobNotFound,
)
from qiskit_ibm_runtime.qiskit_runtime_service import QiskitRuntimeService

from ..decorators import mock_responses
from ..ibm_test_case import IBMTestCase
from ..registries import Job

if TYPE_CHECKING:
    from ..registries import BaseRegistry


class ToIntDecoder(ResultDecoder):
    """Decoder that decodes to `2`."""

    @classmethod
    def decode(cls, data):
        """Decode the result data."""
        return 2


class MultiplierDecoder(ResultDecoder):
    """Decoder that multiplies by `3`."""

    @classmethod
    def decode(cls, data):
        """Decode the result data."""
        return data * 3


def run_program(
    service: QiskitRuntimeService,
    registry: BaseRegistry,
    inputs: dict,
    options: dict,
    backend_name: str = "common_backend",
) -> tuple[RuntimeJobV2, Job]:
    """Run a program using the `service`, and add a corresponding job to the registry.

    This function takes advantage of the `QiskitRuntimeService._run()` method as the entry point
    for executing a job, converting this function's arguments into the form it expects. It also
    adds a corresponding registry `Job` to the `registry`.

    Args:
        service: the `QiskitRuntimeService` to use for running the program.
        registry: the mocked registry for the decorated test.
        inputs: input parameters.
        options: runtime options.
        backend_name: name of the backend to run against.

    Returns:
        The real job which results of the execution of the program, and the registry job that is
        added to the registry.
    """
    options.update({"backend": backend_name, "instance": registry.instances["a"].crn})
    job = service._run("sampler", inputs, options)
    registry_job = Job(
        job.job_id(),
        backend_name,
        program="sampler",
        status="running",
        statuses=["running", "completed"],
    )
    registry.add_job(registry_job, "a")

    return job, registry_job


@ddt
class TestRuntimeJob(IBMTestCase):
    """Class for testing runtime jobs."""

    @mock_responses
    def test_run_program(self, registry):
        """Test running program."""
        service = QiskitRuntimeService(token="my_token")
        job, _ = run_program(service, registry, {"param1": "foo"}, {})

        self.assertTrue(job.job_id())
        self.assertIsInstance(job, RuntimeJobV2)
        job.wait_for_final_state(poll_interval=0.1)
        self.assertEqual(job.status(), "DONE")
        self.assertTrue(job.result())

    @mock_responses
    def test_run_program_phantom_backend(self, registry):
        """Test running on a phantom backend."""
        service = QiskitRuntimeService(token="my_token")
        with self.assertRaises(QiskitBackendNotFoundError):
            run_program(service, registry, {}, {}, backend_name="phantom_backend")

    @mock_responses
    def test_run_program_with_custom_runtime_image(self, registry):
        """Test running program with a custom image."""
        image = "name:tag"
        service = QiskitRuntimeService(token="my_token")
        job, _ = run_program(service, registry, {"param1": "foo"}, {"image": image})

        self.assertTrue(job.job_id())
        self.assertIsInstance(job, RuntimeJobV2)
        job.wait_for_final_state(poll_interval=0.1)
        self.assertTrue(job.result())
        self.assertEqual(job.status(), "DONE")
        self.assertEqual(job.image, image)

    @mock_responses
    def test_run_program_with_custom_log_level(self, registry):
        """Test running program with a custom log level."""
        service = QiskitRuntimeService(token="my_token")
        job, _ = run_program(service, registry, {"param1": "foo"}, {"log_level": "DEBUG"})

        # `log_debug` is not returned by the API, nor present in `RuntimeJobV2`. The assert on
        # this tests just check that the job is valid (and the "log_level" argument was accepted).
        self.assertTrue(job.job_id())
        self.assertIsInstance(job, RuntimeJobV2)
        job.wait_for_final_state(poll_interval=0.1)
        self.assertTrue(job.result())
        self.assertEqual(job.status(), "DONE")

    @mock_responses
    def test_run_program_failed_with_no_reason(self, registry):
        """Test a failed program execution, when no reason is present in the job details."""
        service = QiskitRuntimeService(token="my_token")
        job, registry_job = run_program(service, registry, {}, {})

        # Update the registry job so it fails.
        registry_job.statuses = ["running", "failed"]
        registry_job.statuses_reason = {"failed": (123, "")}
        registry_job.raw_results = json.dumps("Content from results")

        job.wait_for_final_state(poll_interval=0.1)
        job_result_raw = service._get_api_client().job_results(job.job_id())
        self.assertEqual("ERROR", job.status())
        self.assertEqual(
            API_TO_JOB_ERROR_MESSAGE["FAILED"].format(job.job_id(), job_result_raw),
            job.error_message(),
        )

        # When no reason is present in the job details, the error message is based on the raw
        # response from the results.
        self.assertIn("Content from results", job.error_message())
        with self.assertRaisesRegex(RuntimeJobFailureError, "Content from results"):
            job.result()

    @mock_responses
    def test_run_program_failed_with_reason(self, registry):
        """Test a failed program execution, when reason is present in the job details."""
        service = QiskitRuntimeService(token="my_token")
        job, registry_job = run_program(service, registry, {}, {})

        # Update the registry job so it fails.
        registry_job.statuses = ["running", "failed"]
        registry_job.statuses_reason = {"failed": (123, "Some reason")}

        job.wait_for_final_state(poll_interval=0.1)
        self.assertEqual("ERROR", job.status())

        # When a reason is present in the job details, the error message is based on that reason.
        self.assertIn("Some reason", job.error_message())
        with self.assertRaisesRegex(RuntimeJobFailureError, "Some reason"):
            job.result()

    @mock_responses
    def test_run_program_failed_ran_too_long(self, registry):
        """Test a program that failed since it ran longer than maximum execution time."""
        service = QiskitRuntimeService(token="my_token")
        job, registry_job = run_program(service, registry, {}, {})

        # Update the registry job so it fails.
        registry_job.statuses = ["running", "cancelled"]
        registry_job.statuses_reason = {"cancelled": (1305, "RAN TOO LONG")}
        registry_job.raw_results = json.dumps("Content from results")

        job.wait_for_final_state(poll_interval=0.1)
        job_result_raw = service._get_api_client().job_results(job.job_id())
        self.assertEqual("ERROR", job.status())
        self.assertEqual(
            API_TO_JOB_ERROR_MESSAGE["CANCELLED - RAN TOO LONG"].format(
                job.job_id(), job_result_raw
            ),
            job.error_message(),
        )

        # In this specific case, the error message is based on the content from the results, and the
        # exception is based on the reason.
        self.assertIn("Content from results", job.error_message())
        with self.assertRaisesRegex(RuntimeJobMaxTimeoutError, "RAN TOO LONG"):
            job.result()

    @mock_responses
    def test_cancel_job(self, registry):
        """Test canceling a job."""
        service = QiskitRuntimeService(token="my_token")
        job, registry_job = run_program(service, registry, {}, {})

        # Update the registry job so it gets cancelled.
        registry_job.statuses = ["running", "cancelled"]

        job.cancel()
        self.assertEqual(job.status(), "CANCELLED")

        # This automatically advances the job to cancelled.
        remote_job = service.job(job.job_id())
        self.assertEqual(remote_job.status(), "CANCELLED")
        with self.assertRaisesRegex(RuntimeInvalidStateError, "Job was cancelled"):
            remote_job.result()

    @mock_responses
    def test_final_result(self, registry):
        """Test getting final result."""
        service = QiskitRuntimeService(token="my_token")
        job, _ = run_program(service, registry, {}, {})
        job.wait_for_final_state(poll_interval=0.1)
        result = job.result()
        self.assertTrue(result)

    @mock_responses
    def test_job_status(self, registry):
        """Test job status."""
        service = QiskitRuntimeService(token="my_token")
        job, _ = run_program(service, registry, {}, {})
        self.assertTrue(job.status())

    @mock_responses
    def test_wait_for_final_state(self, registry):
        """Test wait for final state."""
        service = QiskitRuntimeService(token="my_token")
        job, _ = run_program(service, registry, {}, {})
        job.wait_for_final_state(poll_interval=0.1)
        self.assertEqual("DONE", job.status())

    @mock_responses
    def test_delete_job(self, registry):
        """Test deleting a job."""
        service = QiskitRuntimeService(token="my_token")
        job, registry_job = run_program(service, registry, {"param1": "foo"}, {})
        self.assertTrue(job.job_id())

        service.delete_job(job.job_id())

        del registry.jobs["a"][registry_job.id]
        with self.assertRaises(RuntimeJobNotFound):
            service.job(job.job_id())

    @mock_responses
    def test_instance_limit_warning(self, registry):
        """Test emitting a warning if instance usage has been reached."""
        service = QiskitRuntimeService(token="my_token")

        # All relevant fields present, account limit reached.
        registry.instances["a"].usage = {
            "usage_consumed_seconds": 1,
            "usage_limit_seconds": 2,
            "usage_limit_reached": True,
        }
        with self.assertWarnsRegex(UserWarning, r"There is currently no more time available"):
            service._run(program_id="sampler", options={"backend": "common_backend"}, inputs={})

        # All relevant fields present, instance limit reached.
        registry.instances["a"].usage = {
            "usage_consumed_seconds": 3,
            "usage_limit_seconds": 2,
            "usage_limit_reached": True,
        }
        with self.assertWarnsRegex(UserWarning, r"This instance has met its usage limit"):
            service._run(program_id="sampler", options={"backend": "common_backend"}, inputs={})

        # Missing `usage_limit_seconds`, account limit reached.
        registry.instances["a"].usage = {
            "usage_consumed_seconds": 1,
            "usage_limit_reached": True,
        }
        with self.assertWarnsRegex(UserWarning, r"There is currently no more time available"):
            service._run(program_id="sampler", options={"backend": "common_backend"}, inputs={})

    @data((None, 0.5), ("some_session_id", 0.1))
    @mock_responses
    def test_wait_for_final_state_poll_interval_defaults(self, id_and_default, registry):
        """wait_for_final_state should use default values if `None` provided."""
        service = QiskitRuntimeService(token="my_token")
        job, _ = run_program(service, registry, {}, {})

        session_id, default = id_and_default
        job._session_id = session_id
        with patch.object(RuntimeJobV2, "status", side_effect=["WAITING", "DONE"]):
            with patch("time.sleep", return_value=None) as patched_sleep:
                job.wait_for_final_state()
                patched_sleep.assert_called_with(default)

    @data(0.99, 0.1, 1.23)
    @mock_responses
    def test_wait_for_final_state_poll_inverval_custom(self, value, registry):
        """Test wait_for_final_state when passing a custom poll interval."""
        service = QiskitRuntimeService(token="my_token")
        job, _ = run_program(service, registry, {}, {})

        expected_interval = value
        with patch.object(RuntimeJobV2, "status", side_effect=["WAITING", "DONE"]):
            with patch("time.sleep", return_value=None) as patched_sleep:
                with warnings.catch_warnings(record=True) as warn_cm:
                    job.wait_for_final_state(poll_interval=value)

                    # Values lower than the floor: limit to the floor, emit warning.
                    if value < 0.1:
                        expected_interval = 0.1
                        self.assertIn("Using 0.1 as the poll interval", str(warn_cm[0]))
                    # Other values: use them as-is, no warning.
                    else:
                        self.assertEqual(len(warn_cm), 0)

                    patched_sleep.assert_called_with(expected_interval)

    @mock_responses
    @data("pending", "complete")
    def test_usage_no_partial(self, status, registry):
        """usage() should return 0 if the status is not `completed`."""
        usage = {"qpu_charge_time_seconds": 123, "status": status}
        registry.add_job(Job("my_job", "common_backend", usage=usage), "a")
        service = QiskitRuntimeService(token="my_token")

        job = service.job("my_job")
        usage = job.usage()
        self.assertEqual(usage, 0 if status == "pending" else 123)

    @mock_responses
    @data("pending", "complete")
    def test_usage_partial(self, status, registry):
        """usage() should always return `qpu_charge_time_seconds` regardless of status."""
        usage = {"qpu_charge_time_seconds": 123, "status": status}
        registry.add_job(Job("my_job", "common_backend", usage=usage), "a")
        service = QiskitRuntimeService(token="my_token")

        job = service.job("my_job")
        usage = job.usage(partial=True)
        self.assertEqual(usage, 123)

    @data(None, ToIntDecoder, [ToIntDecoder, MultiplierDecoder])
    @mock_responses
    def test_result_decoders_is_always_sequence(self, decoders, registry):
        """`job._result_decoders` should always be a list after instantiating."""
        service = QiskitRuntimeService(token="my_token")

        job = RuntimeJobV2(
            backend=None,
            api_client=service._active_api_client,
            job_id="123",
            program_id="blah",
            service=service,
            result_decoder=decoders,
        )

        self.assertIsInstance(job._result_decoders, list)

    @mock_responses
    def test_result_chains_decoders(self, registry):
        """When passing a list of decoders to `result()`, they are chained."""
        results = json.dumps({"some": "response"})
        registry.add_job(Job("my_job", "common_backend", raw_results=results), "a")
        service = QiskitRuntimeService(token="my_token")

        job = service.job("my_job")

        self.assertEqual(job.result(decoder=ToIntDecoder), 2)
        self.assertEqual(job.result(decoder=[ToIntDecoder, MultiplierDecoder]), 2 * 3)
