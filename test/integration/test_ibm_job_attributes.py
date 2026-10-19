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

import pytest
from dateutil import tz
from pydantic import ValidationError
from qiskit.compiler import transpile

from qiskit_ibm_runtime import SamplerV2 as Sampler
from qiskit_ibm_runtime.exceptions import IBMInputValueError

from ..utils import bell

if TYPE_CHECKING:
    from qiskit_ibm_runtime import RuntimeJobV2
    from qiskit_ibm_runtime.ibm_backend import IBMBackend

    from .dependencies import Dependencies


@pytest.fixture(scope="class")
def job_test_backend(backend_test: IBMBackend | None) -> RuntimeJobV2:
    """Return the job used by the tests in the class, submitted to the test backend."""
    return Sampler(mode=backend_test).run([transpile(bell(), backend_test)])


class TestIBMJobAttributes:
    """Test the attributes of a submitted IBMJob."""

    def test_job_id(self, job_test_backend: RuntimeJobV2) -> None:
        """Test getting a job ID."""
        assert job_test_backend.job_id() is not None

    def test_job_instance(self, job_test_backend: RuntimeJobV2, dependencies: Dependencies) -> None:
        """Test getting job instance."""
        assert dependencies.instance == job_test_backend.instance

    def test_get_backend_name(
        self, job_test_backend: RuntimeJobV2, backend_test: IBMBackend | None
    ) -> None:
        """Test getting a backend name."""
        assert job_test_backend.backend().name == backend_test.name

    def test_cost_estimation(self, job_test_backend: RuntimeJobV2) -> None:
        """Test cost estimation is returned correctly."""
        assert job_test_backend.usage_estimation
        assert "quantum_seconds" in job_test_backend.usage_estimation


class TestIBMJobSubmission:
    """Test the attributes of jobs submitted with different options."""

    def test_job_creation_date(self, backend_test: IBMBackend | None) -> None:
        """Test retrieving creation date, while ensuring it is in local time."""
        # datetime, before running the job, in local time.
        start_datetime = datetime.now().replace(tzinfo=tz.tzlocal()) - timedelta(minutes=1)
        sampler = Sampler(mode=backend_test)
        job = sampler.run([transpile(bell(), backend_test)])
        job.result()
        # datetime, after the job is done running, in local time.
        end_datetime = datetime.now().replace(tzinfo=tz.tzlocal()) + timedelta(minutes=1)

        assert start_datetime <= job.creation_date <= end_datetime

    def test_job_tags(self, backend_test: IBMBackend | None, dependencies: Dependencies) -> None:
        """Test using job tags."""
        service = dependencies.service
        last_week = datetime.now() - timedelta(days=7)
        # Use a unique tag.
        job_tags = [
            uuid.uuid4().hex[0:16],
            uuid.uuid4().hex[0:16],
            uuid.uuid4().hex[0:16],
        ]
        sampler = Sampler(mode=backend_test)
        sampler.options.environment.job_tags = job_tags  # type: ignore[union-attr]
        job = sampler.run([transpile(bell(), backend_test)])
        assert job.tags

        non_matching_tags = [job_tags[0:1] + ["phantom_tags"], ["phantom_tag"]]
        for tags in non_matching_tags:
            found_jobs = service.jobs(job_tags=tags, created_after=last_week)
            assert len(found_jobs) == 0

        matching_tags = [job_tags, job_tags[1:3]]
        for tags in matching_tags:
            found_jobs = service.jobs(job_tags=tags, created_after=last_week)
            assert len(found_jobs) == 1
            assert found_jobs[0].job_id() == job.job_id()
            assert set(found_jobs[0].tags) == set(job_tags)

    def test_job_tags_replace(self, backend_test: IBMBackend | None) -> None:
        """Test updating job tags by replacing a job's existing tags."""
        initial_job_tags = [uuid.uuid4().hex[:16]]
        sampler = Sampler(mode=backend_test)
        sampler.options.environment.job_tags = initial_job_tags  # type: ignore[union-attr]
        job = sampler.run([transpile(bell(), backend_test)])

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
            assert set(new_tags) == set(job.tags)

    def test_invalid_job_tags(
        self, backend_test: IBMBackend | None, dependencies: Dependencies
    ) -> None:
        """Test using job tags with an and operator."""
        service = dependencies.service
        with pytest.raises(ValidationError):
            sampler = Sampler(mode=backend_test)
            sampler.options.environment.job_tags = "foo"  # type: ignore[union-attr]

        with pytest.raises(IBMInputValueError):
            service.jobs(job_tags=[1, 2, 3])  # type: ignore[list-item]

    def test_private_option(self, dependencies: Dependencies) -> None:
        """Test private option."""
        backend = dependencies.service.backend(dependencies.qpu)

        sampler = Sampler(mode=backend)
        sampler.options.environment.private = True  # type: ignore[union-attr]
        bell_circuit = transpile(bell(), backend)
        job = sampler.run([bell_circuit])
        assert not job.inputs
        assert job.result()
        assert not job.result()  # private job results can only be retrieved once
        assert job.private
