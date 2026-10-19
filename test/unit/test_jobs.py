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

import pytest
from qiskit.providers.exceptions import QiskitBackendNotFoundError

from qiskit_ibm_runtime import RuntimeJobV2
from qiskit_ibm_runtime.decoders.result_decoder import ResultDecoder
from qiskit_ibm_runtime.exceptions import (
    RuntimeInvalidStateError,
    RuntimeJobFailureError,
    RuntimeJobMaxTimeoutError,
    RuntimeJobNotFound,
)
from qiskit_ibm_runtime.qiskit_runtime_service import QiskitRuntimeService
from qiskit_ibm_runtime.runtime_job_v2 import API_TO_JOB_ERROR_MESSAGE

from ..registries import Backend, Job, OneInstanceDryRunRegistry

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
    dry_run: bool = False,
    instance: str = "a",
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
        dry_run: whether to execute in dry_run mode.
        instance: the instance where the job will be appended to.

    Returns:
        The real job which results of the execution of the program, and the registry job that is
        added to the registry.
    """
    options.update({"backend": backend_name, "instance": registry.instances[instance].crn})
    job = service._run("sampler", inputs, options, dry_run=dry_run)
    registry_job = Job(
        job.job_id(),
        backend_name,
        program="sampler",
        status="running",
        statuses=["running", "completed"],
    )
    registry.add_job(registry_job, instance)

    return job, registry_job


class TestRuntimeJob:
    """Class for testing runtime jobs."""

    def test_run_program(self, registry: BaseRegistry) -> None:
        """Test running program."""
        service = QiskitRuntimeService(token="my_token")
        job, _ = run_program(service, registry, {"param1": "foo"}, {})

        assert job.job_id()
        assert isinstance(job, RuntimeJobV2)
        job.wait_for_final_state(poll_interval=0.1)
        assert job.status() == "DONE"
        assert job.result()

    def test_run_program_phantom_backend(self, registry: BaseRegistry) -> None:
        """Test running on a phantom backend."""
        service = QiskitRuntimeService(token="my_token")
        with pytest.raises(QiskitBackendNotFoundError):
            run_program(service, registry, {}, {}, backend_name="phantom_backend")

    def test_run_program_with_custom_runtime_image(self, registry: BaseRegistry) -> None:
        """Test running program with a custom image."""
        image = "name:tag"
        service = QiskitRuntimeService(token="my_token")
        job, _ = run_program(service, registry, {"param1": "foo"}, {"image": image})

        assert job.job_id()
        assert isinstance(job, RuntimeJobV2)
        job.wait_for_final_state(poll_interval=0.1)
        assert job.result()
        assert job.status() == "DONE"
        assert job.image == image

    def test_run_program_with_custom_log_level(self, registry: BaseRegistry) -> None:
        """Test running program with a custom log level."""
        service = QiskitRuntimeService(token="my_token")
        job, _ = run_program(service, registry, {"param1": "foo"}, {"log_level": "DEBUG"})

        # `log_debug` is not returned by the API, nor present in `RuntimeJobV2`. The assert on
        # this tests just check that the job is valid (and the "log_level" argument was accepted).
        assert job.job_id()
        assert isinstance(job, RuntimeJobV2)
        job.wait_for_final_state(poll_interval=0.1)
        assert job.result()
        assert job.status() == "DONE"

    def test_run_program_failed_with_no_reason(self, registry: BaseRegistry) -> None:
        """Test a failed program execution, when no reason is present in the job details."""
        service = QiskitRuntimeService(token="my_token")
        job, registry_job = run_program(service, registry, {}, {})

        # Update the registry job so it fails.
        registry_job.statuses = ["running", "failed"]
        registry_job.statuses_reason = {"failed": (123, "")}
        registry_job.raw_results = json.dumps("Content from results")

        job.wait_for_final_state(poll_interval=0.1)
        job_result_raw = service._get_api_client().job_results(job.job_id())
        assert "ERROR" == job.status()
        assert (
            API_TO_JOB_ERROR_MESSAGE["FAILED"].format(job.job_id(), job_result_raw)
            == job.error_message()
        )

        # When no reason is present in the job details, the error message is based on the raw
        # response from the results.
        assert "Content from results" in job.error_message()
        with pytest.raises(RuntimeJobFailureError, match="Content from results"):
            job.result()

    def test_run_program_failed_with_reason(self, registry: BaseRegistry) -> None:
        """Test a failed program execution, when reason is present in the job details."""
        service = QiskitRuntimeService(token="my_token")
        job, registry_job = run_program(service, registry, {}, {})

        # Update the registry job so it fails.
        registry_job.statuses = ["running", "failed"]
        registry_job.statuses_reason = {"failed": (123, "Some reason")}

        job.wait_for_final_state(poll_interval=0.1)
        assert "ERROR" == job.status()

        # When a reason is present in the job details, the error message is based on that reason.
        assert "Some reason" in job.error_message()
        with pytest.raises(RuntimeJobFailureError, match="Some reason"):
            job.result()

    def test_run_program_failed_ran_too_long(self, registry: BaseRegistry) -> None:
        """Test a program that failed since it ran longer than maximum execution time."""
        service = QiskitRuntimeService(token="my_token")
        job, registry_job = run_program(service, registry, {}, {})

        # Update the registry job so it fails.
        registry_job.statuses = ["running", "cancelled"]
        registry_job.statuses_reason = {"cancelled": (1305, "RAN TOO LONG")}
        registry_job.raw_results = json.dumps("Content from results")

        job.wait_for_final_state(poll_interval=0.1)
        job_result_raw = service._get_api_client().job_results(job.job_id())
        assert "ERROR" == job.status()
        assert (
            API_TO_JOB_ERROR_MESSAGE["CANCELLED - RAN TOO LONG"].format(
                job.job_id(), job_result_raw
            )
            == job.error_message()
        )

        # In this specific case, the error message is based on the content from the results, and the
        # exception is based on the reason.
        assert "Content from results" in job.error_message()
        with pytest.raises(RuntimeJobMaxTimeoutError, match="RAN TOO LONG"):
            job.result()

    @pytest.mark.registry(registry_class=OneInstanceDryRunRegistry)
    def test_run_program_dry_run(self, registry: BaseRegistry) -> None:
        """Running a program with `dry_run` should execute against the mock backend."""
        service = QiskitRuntimeService(token="my_token")
        job, _ = run_program(service, registry, {}, {}, backend_name="ibm_foo", dry_run=True)
        job.wait_for_final_state(poll_interval=0.1)
        assert job.backend().name == "mock_foo"

    def test_run_program_dry_run_no_mocked_backend(self, registry: BaseRegistry) -> None:
        """Running a program with `dry_run` should fail if the mock backend cannot be found."""
        service = QiskitRuntimeService(token="my_token")
        # Registry has `common_backend`, but no `common_backend`.
        with pytest.raises(QiskitBackendNotFoundError, match="'mock_backend' was not found"):
            run_program(service, registry, {}, {}, dry_run=True)

    def test_run_program_dry_run_mock_in_other_instance(self, registry: BaseRegistry) -> None:
        """Running a program with `dry_run` should pick up mock backends in other instances."""
        # Add "mock_backend_a" to instance "b", while "unique_backend_a" is in instance "a".
        registry.add_backend(Backend("mock_backend_a"), "b")

        service = QiskitRuntimeService(token="my_token")
        job, _ = run_program(
            service, registry, {}, {}, backend_name="unique_backend_a", dry_run=True, instance="b"
        )
        job.wait_for_final_state(poll_interval=0.1)
        assert job.backend().name == "mock_backend_a"

    def test_cancel_job(self, registry: BaseRegistry) -> None:
        """Test canceling a job."""
        service = QiskitRuntimeService(token="my_token")
        job, registry_job = run_program(service, registry, {}, {})

        # Update the registry job so it gets cancelled.
        registry_job.statuses = ["running", "cancelled"]

        job.cancel()
        assert job.status() == "CANCELLED"

        # This automatically advances the job to cancelled.
        remote_job = service.job(job.job_id())
        assert remote_job.status() == "CANCELLED"
        with pytest.raises(RuntimeInvalidStateError, match="Job was cancelled"):
            remote_job.result()

    def test_final_result(self, registry: BaseRegistry) -> None:
        """Test getting final result."""
        service = QiskitRuntimeService(token="my_token")
        job, _ = run_program(service, registry, {}, {})
        job.wait_for_final_state(poll_interval=0.1)
        result = job.result()
        assert result

    def test_job_status(self, registry: BaseRegistry) -> None:
        """Test job status."""
        service = QiskitRuntimeService(token="my_token")
        job, _ = run_program(service, registry, {}, {})
        assert job.status()

    def test_wait_for_final_state(self, registry: BaseRegistry) -> None:
        """Test wait for final state."""
        service = QiskitRuntimeService(token="my_token")
        job, _ = run_program(service, registry, {}, {})
        job.wait_for_final_state(poll_interval=0.1)
        assert "DONE" == job.status()

    def test_delete_job(self, registry: BaseRegistry) -> None:
        """Test deleting a job."""
        service = QiskitRuntimeService(token="my_token")
        job, registry_job = run_program(service, registry, {"param1": "foo"}, {})
        assert job.job_id()

        service.delete_job(job.job_id())

        del registry.jobs["a"][registry_job.id]
        with pytest.raises(RuntimeJobNotFound):
            service.job(job.job_id())

    def test_instance_limit_warning(self, registry: BaseRegistry) -> None:
        """Test emitting a warning if instance usage has been reached."""
        service = QiskitRuntimeService(token="my_token")

        # All relevant fields present, account limit reached.
        registry.instances["a"].usage = {
            "usage_consumed_seconds": 1,
            "usage_limit_seconds": 2,
            "usage_limit_reached": True,
        }
        with pytest.warns(UserWarning, match=r"There is currently no more time available"):
            service._run(program_id="sampler", options={"backend": "common_backend"}, inputs={})

        # All relevant fields present, instance limit reached.
        registry.instances["a"].usage = {
            "usage_consumed_seconds": 3,
            "usage_limit_seconds": 2,
            "usage_limit_reached": True,
        }
        with pytest.warns(UserWarning, match=r"This instance has met its usage limit"):
            service._run(program_id="sampler", options={"backend": "common_backend"}, inputs={})

        # Missing `usage_limit_seconds`, account limit reached.
        registry.instances["a"].usage = {
            "usage_consumed_seconds": 1,
            "usage_limit_reached": True,
        }
        with pytest.warns(UserWarning, match=r"There is currently no more time available"):
            service._run(program_id="sampler", options={"backend": "common_backend"}, inputs={})

    @pytest.mark.parametrize("id_and_default", [(None, 0.5), ("some_session_id", 0.1)])
    def test_wait_for_final_state_poll_interval_defaults(
        self, id_and_default: tuple[str, float], registry: BaseRegistry
    ) -> None:
        """wait_for_final_state should use default values if `None` provided."""
        service = QiskitRuntimeService(token="my_token")
        job, _ = run_program(service, registry, {}, {})

        session_id, default = id_and_default
        job._session_id = session_id
        with patch.object(RuntimeJobV2, "status", side_effect=["WAITING", "DONE"]):
            with patch("time.sleep", return_value=None) as patched_sleep:
                job.wait_for_final_state()
                patched_sleep.assert_called_with(default)

    @pytest.mark.parametrize("value", [0.99, 0.1, 1.23])
    def test_wait_for_final_state_poll_inverval_custom(
        self, value: float, registry: BaseRegistry
    ) -> None:
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
                        assert "Using 0.1 as the poll interval" in str(warn_cm[0])
                    # Other values: use them as-is, no warning.
                    else:
                        assert len(warn_cm) == 0

                    patched_sleep.assert_called_with(expected_interval)

    @pytest.mark.parametrize("status", ["pending", "complete"])
    def test_usage_no_partial(self, status: str, registry: BaseRegistry) -> None:
        """usage() should return 0 if the status is not `completed`."""
        usage = {"qpu_charge_time_seconds": 123, "status": status}
        registry.add_job(Job("my_job", "common_backend", usage=usage), "a")
        service = QiskitRuntimeService(token="my_token")

        job = service.job("my_job")
        float_usage = job.usage()
        assert float_usage == (0 if status == "pending" else 123)

    @pytest.mark.parametrize("status", ["pending", "complete"])
    def test_usage_partial(self, status: str, registry: BaseRegistry) -> None:
        """usage() should always return `qpu_charge_time_seconds` regardless of status."""
        usage = {"qpu_charge_time_seconds": 123, "status": status}
        registry.add_job(Job("my_job", "common_backend", usage=usage), "a")
        service = QiskitRuntimeService(token="my_token")

        job = service.job("my_job")
        float_usage = job.usage(partial=True)
        assert float_usage == 123

    @pytest.mark.parametrize("decoders", [None, ToIntDecoder, [ToIntDecoder, MultiplierDecoder]])
    def test_result_decoders_is_always_sequence(
        self, decoders: None | ResultDecoder | list[ResultDecoder], registry: BaseRegistry
    ) -> None:
        """`job._result_decoders` should always be a list after instantiating."""
        service = QiskitRuntimeService(token="my_token")

        job = RuntimeJobV2(
            backend=None,
            api_client=service._active_api_client,
            job_id="123",
            program_id="blah",
            service=service,
            result_decoder=decoders,  # type: ignore[arg-type]
        )

        assert isinstance(job._result_decoders, list)

    def test_result_chains_decoders(self, registry: BaseRegistry) -> None:
        """When passing a list of decoders to `result()`, they are chained."""
        results = json.dumps({"some": "response"})
        registry.add_job(Job("my_job", "common_backend", raw_results=results), "a")
        service = QiskitRuntimeService(token="my_token")

        job = service.job("my_job")

        assert job.result(decoder=ToIntDecoder) == 2
        assert job.result(decoder=[ToIntDecoder, MultiplierDecoder]) == 2 * 3
