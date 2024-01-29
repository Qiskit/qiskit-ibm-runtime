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

"""Test IBMJob attributes."""

import uuid
import time
from datetime import datetime, timedelta
from unittest import skip, SkipTest

from dateutil import tz
from qiskit.compiler import transpile
from qiskit import QuantumCircuit
from qiskit.providers.jobstatus import JobStatus, JOB_FINAL_STATES

from qiskit_ibm_runtime.exceptions import IBMBackendValueError

from qiskit_ibm_runtime import IBMBackend, RuntimeJob
from qiskit_ibm_runtime.exceptions import IBMInputValueError
from ..decorators import (
    IntegrationTestDependencies,
    integration_test_setup,
)
from ..ibm_test_case import IBMTestCase
from ..utils import most_busy_backend, cancel_job_safe, bell


class TestIBMJobAttributes(IBMTestCase):
    """Test IBMJob instance attributes."""

    sim_backend: IBMBackend
    bell: QuantumCircuit
    sim_job: RuntimeJob
    last_week: datetime

    @classmethod
    @integration_test_setup()
    def setUpClass(cls, dependencies: IntegrationTestDependencies) -> None:
        """Initial class level setup."""
        # pylint: disable=arguments-differ
        super().setUpClass()
        cls.dependencies = dependencies
        cls.service = dependencies.service
        cls.sim_backend = dependencies.service.backend("ibmq_qasm_simulator")
        cls.bell = transpile(bell(), cls.sim_backend)
        cls.sim_job = cls.sim_backend.run(cls.bell)
        cls.last_week = datetime.now() - timedelta(days=7)

    def setUp(self):
        """Initial test setup."""
        super().setUp()
        self._qc = bell()

    def test_job_id(self):
        """Test getting a job ID."""
        self.assertTrue(self.sim_job.job_id() is not None)

    def test_get_backend_name(self):
        """Test getting a backend name."""
        self.assertTrue(self.sim_job.backend().name == self.sim_backend.name)

    def test_job_creation_date(self):
        """Test retrieving creation date, while ensuring it is in local time."""
        # datetime, before running the job, in local time.
        start_datetime = datetime.now().replace(tzinfo=tz.tzlocal()) - timedelta(seconds=1)
        job = self.sim_backend.run(self.bell)
        job.result()
        # datetime, after the job is done running, in local time.
        end_datetime = datetime.now().replace(tzinfo=tz.tzlocal()) + timedelta(seconds=1)

        self.assertTrue(
            (start_datetime <= job.creation_date <= end_datetime),
            "job creation date {} is not "
            "between the start date time {} and end date time {}".format(
                job.creation_date, start_datetime, end_datetime
            ),
        )

    def test_esp_readout_not_enabled(self):
        """Test that an error is thrown if ESP readout is used and the backend does not support it."""
        # sim backend does not have ``measure_esp_enabled`` flag: defaults to ``False``
        with self.assertRaises(IBMBackendValueError) as context_manager:
            self.sim_backend.run(self.bell, use_measure_esp=True)
        self.assertIn(
            "ESP readout not supported on this device. Please make sure the flag "
            "'use_measure_esp' is unset or set to 'False'.",
            context_manager.exception.message,
        )

    def test_esp_readout_enabled(self):
        """Test that ESP readout can be used when the backend supports it."""
        try:
            setattr(self.sim_backend._configuration, "measure_esp_enabled", True)
            job = self.sim_backend.run(self.bell, use_measure_esp=True)
            self.assertEqual(job.inputs["use_measure_esp"], True)
        finally:
            delattr(self.sim_backend._configuration, "measure_esp_enabled")

    def test_esp_readout_default_value(self):
        """Test that ESP readout is set to backend support value if not specified."""
        try:
            # ESP readout not enabled on backend
            setattr(self.sim_backend._configuration, "measure_esp_enabled", False)
            job = self.sim_backend.run(self.bell)
            self.assertIsNone(getattr(job.inputs, "use_measure_esp", None))
            # ESP readout enabled on backend
            setattr(self.sim_backend._configuration, "measure_esp_enabled", True)
            job = self.sim_backend.run(self.bell, use_measure_esp=True)
            self.assertEqual(job.inputs["use_measure_esp"], True)
        finally:
            delattr(self.sim_backend._configuration, "measure_esp_enabled")

    def test_job_tags(self):
        """Test using job tags."""
        # Use a unique tag.
        job_tags = [
            uuid.uuid4().hex[0:16],
            uuid.uuid4().hex[0:16],
            uuid.uuid4().hex[0:16],
        ]
        job = self.sim_backend.run(self.bell, job_tags=job_tags)

        no_rjobs_tags = [job_tags[0:1] + ["phantom_tags"], ["phantom_tag"]]
        for tags in no_rjobs_tags:
            rjobs = self.service.jobs(job_tags=tags, created_after=self.last_week)
            self.assertEqual(len(rjobs), 0, "Expected job {}, got {}".format(job.job_id(), rjobs))

        has_rjobs_tags = [job_tags, job_tags[1:3]]
        for tags in has_rjobs_tags:
            with self.subTest(tags=tags):
                rjobs = self.service.jobs(
                    job_tags=tags,
                    created_after=self.last_week,
                )
                self.assertEqual(
                    len(rjobs), 1, "Expected job {}, got {}".format(job.job_id(), rjobs)
                )
                self.assertEqual(rjobs[0].job_id(), job.job_id())
                self.assertEqual(set(rjobs[0].tags), set(job_tags))

    def test_job_tags_replace(self):
        """Test updating job tags by replacing a job's existing tags."""
        initial_job_tags = [uuid.uuid4().hex[:16]]
        job = self.sim_backend.run(self.bell, job_tags=initial_job_tags)

        tags_to_replace_subtests = [
            [],  # empty tags.
            list("{}_new_tag_{}".format(uuid.uuid4().hex[:5], i) for i in range(2)),  # unique tags.
            initial_job_tags + ["foo"],
        ]
        for tags_to_replace in tags_to_replace_subtests:
            with self.subTest(tags_to_replace=tags_to_replace):
                # Update the job tags.
                _ = job.update_tags(new_tags=tags_to_replace)

                # Wait a bit so we don't get cached results.
                time.sleep(2)
                self.assertEqual(set(tags_to_replace), set(job.tags))

    def test_invalid_job_tags(self):
        """Test using job tags with an and operator."""
        self.assertRaises(IBMInputValueError, self.sim_backend.run, self.bell, job_tags={"foo"})
        self.assertRaises(
            IBMInputValueError,
            self.service.jobs,
            job_tags=[1, 2, 3],
        )

    def test_cost_estimation(self):
        """Test cost estimation is returned correctly."""
        self.assertTrue(self.sim_job.usage_estimation)
        self.assertIn("quantum_seconds", self.sim_job.usage_estimation)

    @skip("time_per_step supported in provider but not in runtime")
    def test_time_per_step(self):
        """Test retrieving time per step, while ensuring the date times are in local time."""
        # datetime, before running the job, in local time.
        start_datetime = datetime.now().replace(tzinfo=tz.tzlocal()) - timedelta(seconds=1)
        job = self.sim_backend.run(self.bell)
        job.result()
        # datetime, after the job is done running, in local time.
        end_datetime = datetime.now().replace(tzinfo=tz.tzlocal()) + timedelta(seconds=1)

        self.assertTrue(job.time_per_step())
        for step, time_data in job.time_per_step().items():
            self.assertTrue(
                (start_datetime <= time_data <= end_datetime),
                'job time step "{}={}" is not '
                "between the start date time {} and end date time {}".format(
                    step, time_data, start_datetime, end_datetime
                ),
            )
        rjob = self.service.job(job.job_id())
        self.assertTrue(rjob.time_per_step())

    def test_queue_info(self):
        """Test retrieving queue information."""
        if self.dependencies.channel == "ibm_cloud":
            raise SkipTest("Not supported on cloud channel.")
        # Find the most busy backend.
        backend = most_busy_backend(self.service)
        leave_states = list(JOB_FINAL_STATES) + [JobStatus.RUNNING]
        job = backend.run(self.bell)
        queue_info = None
        for _ in range(20):
            queue_info = job.queue_info()
            # Even if job status is queued, its queue info may not be immediately available.
            if (
                job._status is JobStatus.QUEUED and job.queue_position() is not None
            ) or job._status in leave_states:
                break
            time.sleep(1)

        if job._status is JobStatus.QUEUED and job.queue_position() is not None:
            self.log.debug(
                "Job id=%s, queue info=%s, queue position=%s",
                job.job_id(),
                queue_info,
                job.queue_position(),
            )
            msg = "Job {} is queued but has no ".format(job.job_id())
            self.assertIsNotNone(queue_info, msg + "queue info.")
            self.assertTrue(queue_info.format())
            self.assertTrue(repr(queue_info))
        elif job._status is not None:
            self.assertIsNone(job.queue_position())
            self.log.warning("Unable to retrieve queue information")

        # Cancel job so it doesn't consume more resources.
        cancel_job_safe(job, self.log)
