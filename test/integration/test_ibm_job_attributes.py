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

"""Test IBMJob attributes."""

from __future__ import annotations

import time
import uuid
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from dateutil import tz
from pydantic import ValidationError
from qiskit.compiler import transpile

from qiskit_ibm_runtime import SamplerV2 as Sampler
from qiskit_ibm_runtime.exceptions import IBMInputValueError

from ..utils import bell
from .case import IBMIntegrationJobTestCase

if TYPE_CHECKING:
    from qiskit_ibm_runtime import RuntimeJobV2


class TestIBMJobAttributes(IBMIntegrationJobTestCase):
    """Test the attributes of a submitted IBMJob."""

    test_job: RuntimeJobV2

    @classmethod
    def setUpClass(cls) -> None:
        """Initial class level setup."""
        super().setUpClass()
        cls.test_job = Sampler(mode=cls.test_backend).run([transpile(bell(), cls.test_backend)])

    def test_job_id(self):
        """Test getting a job ID."""
        self.assertTrue(self.test_job.job_id() is not None)

    def test_job_instance(self):
        """Test getting job instance."""
        self.assertEqual(self.dependencies.instance, self.test_job.instance)

    def test_get_backend_name(self):
        """Test getting a backend name."""
        self.assertTrue(self.test_job.backend().name == self.test_backend.name)

    def test_cost_estimation(self):
        """Test cost estimation is returned correctly."""
        self.assertTrue(self.test_job.usage_estimation)
        self.assertIn("quantum_seconds", self.test_job.usage_estimation)


class TestIBMJobSubmission(IBMIntegrationJobTestCase):
    """Test the attributes of jobs submitted with different options."""

    def test_job_creation_date(self):
        """Test retrieving creation date, while ensuring it is in local time."""
        # datetime, before running the job, in local time.
        start_datetime = datetime.now().replace(tzinfo=tz.tzlocal()) - timedelta(minutes=1)
        sampler = Sampler(mode=self.test_backend)
        job = sampler.run([transpile(bell(), self.test_backend)])
        job.result()
        # datetime, after the job is done running, in local time.
        end_datetime = datetime.now().replace(tzinfo=tz.tzlocal()) + timedelta(minutes=1)

        self.assertTrue(
            (start_datetime <= job.creation_date <= end_datetime),
            f"job creation date {job.creation_date} is not "
            f"between the start date time {start_datetime} and end date time {end_datetime}",
        )

    def test_job_tags(self):
        """Test using job tags."""
        service = self.service
        last_week = datetime.now() - timedelta(days=7)
        # Use a unique tag.
        job_tags = [
            uuid.uuid4().hex[0:16],
            uuid.uuid4().hex[0:16],
            uuid.uuid4().hex[0:16],
        ]
        sampler = Sampler(mode=self.test_backend)
        sampler.options.environment.job_tags = job_tags
        job = sampler.run([transpile(bell(), self.test_backend)])
        self.assertTrue(job.tags)

        non_matching_tags = [job_tags[0:1] + ["phantom_tags"], ["phantom_tag"]]
        for tags in non_matching_tags:
            found_jobs = service.jobs(job_tags=tags, created_after=last_week)
            self.assertEqual(len(found_jobs), 0, f"Expected no jobs, got {found_jobs}")

        matching_tags = [job_tags, job_tags[1:3]]
        for tags in matching_tags:
            found_jobs = service.jobs(job_tags=tags, created_after=last_week)
            self.assertEqual(len(found_jobs), 1, f"Expected job {job.job_id()}, got {found_jobs}")
            self.assertEqual(found_jobs[0].job_id(), job.job_id())
            self.assertEqual(set(found_jobs[0].tags), set(job_tags))

    def test_job_tags_replace(self):
        """Test updating job tags by replacing a job's existing tags."""
        initial_job_tags = [uuid.uuid4().hex[:16]]
        sampler = Sampler(mode=self.test_backend)
        sampler.options.environment.job_tags = initial_job_tags
        job = sampler.run([transpile(bell(), self.test_backend)])

        new_tags_cases = [
            [],  # empty tags.
            [f"{uuid.uuid4().hex[:5]}_new_tag_{i}" for i in range(2)],  # unique tags.
            initial_job_tags + ["foo"],  # the initial tags, plus an extra one.
        ]
        for new_tags in new_tags_cases:
            # Update the job tags.
            _ = job.update_tags(new_tags=new_tags)

            # Wait a bit so we don't get cached results.
            time.sleep(2)
            self.assertEqual(set(new_tags), set(job.tags))

    def test_invalid_job_tags(self):
        """Test using job tags with an and operator."""
        service = self.service
        with self.assertRaises(ValidationError):
            sampler = Sampler(mode=self.test_backend)
            sampler.options.environment.job_tags = "foo"

        self.assertRaises(
            IBMInputValueError,
            service.jobs,
            job_tags=[1, 2, 3],
        )

    def test_private_option(self):
        """Test private option."""
        backend = self.dependencies.service.backend(self.dependencies.qpu)

        sampler = Sampler(mode=backend)
        sampler.options.environment.private = True
        bell_circuit = transpile(bell(), backend)
        job = sampler.run([bell_circuit])
        self.assertFalse(job.inputs)
        self.assertTrue(job.result())
        self.assertFalse(job.result())  # private job results can only be retrieved once
        self.assertTrue(job.private)
