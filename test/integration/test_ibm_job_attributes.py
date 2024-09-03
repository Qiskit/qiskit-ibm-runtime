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
from unittest import SkipTest
from pydantic import ValidationError

from dateutil import tz
from qiskit.compiler import transpile
from qiskit import QuantumCircuit


from qiskit_ibm_runtime import IBMBackend, RuntimeJob, SamplerV2 as Sampler
from qiskit_ibm_runtime.exceptions import IBMInputValueError
from ..decorators import (
    IntegrationTestDependencies,
    integration_test_setup,
)
from ..ibm_test_case import IBMTestCase
from ..utils import bell


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
        sampler = Sampler(backend=cls.sim_backend)
        cls.sim_job = sampler.run([cls.bell])
        cls.last_week = datetime.now() - timedelta(days=7)

    def setUp(self):
        """Initial test setup."""
        super().setUp()
        self._qc = bell()

    def test_job_id(self):
        """Test getting a job ID."""
        self.assertTrue(self.sim_job.job_id() is not None)

    def test_job_instance(self):
        """Test getting job instance."""
        if self.dependencies.channel == "ibm_cloud":
            raise SkipTest("Cloud channel instance is not returned.")
        self.assertEqual(self.dependencies.instance, self.sim_job.instance)

    def test_get_backend_name(self):
        """Test getting a backend name."""
        self.assertTrue(self.sim_job.backend().name == self.sim_backend.name)

    def test_job_creation_date(self):
        """Test retrieving creation date, while ensuring it is in local time."""
        # datetime, before running the job, in local time.
        start_datetime = datetime.now().replace(tzinfo=tz.tzlocal()) - timedelta(seconds=1)
        sampler = Sampler(backend=self.sim_backend)
        job = sampler.run([self.bell])
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

    def test_job_tags(self):
        """Test using job tags."""
        # Use a unique tag.
        job_tags = [
            uuid.uuid4().hex[0:16],
            uuid.uuid4().hex[0:16],
            uuid.uuid4().hex[0:16],
        ]
        sampler = Sampler(backend=self.sim_backend)
        sampler.options.environment.job_tags = job_tags
        job = sampler.run([self.bell])

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
        sampler = Sampler(backend=self.sim_backend)
        sampler.options.environment.job_tags = initial_job_tags
        job = sampler.run([self.bell])

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

        with self.assertRaises(ValidationError):
            sampler = Sampler(backend=self.sim_backend)
            sampler.options.environment.job_tags = "foo"

        self.assertRaises(
            IBMInputValueError,
            self.service.jobs,
            job_tags=[1, 2, 3],
        )

    def test_cost_estimation(self):
        """Test cost estimation is returned correctly."""
        self.assertTrue(self.sim_job.usage_estimation)
        self.assertIn("quantum_seconds", self.sim_job.usage_estimation)

    def test_private_option(self):
        """Test private option."""
        try:
            backend = self.service.backend("test_eagle")
        except:
            raise SkipTest("test_eagle not available in this environment")

        sampler = Sampler(mode=backend)
        sampler.options.environment.private = True
        bell_circuit = transpile(bell(), backend)
        job = sampler.run([bell_circuit])
        self.assertFalse(job.inputs)
        self.assertTrue(job.result())
        self.assertFalse(job.result())  # private job results can only be retrieved once
