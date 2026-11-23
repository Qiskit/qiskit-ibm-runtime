# This code is part of Qiskit.
#
# (C) Copyright IBM 2026.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Fixtures shared by the integration tests."""

from __future__ import annotations

import logging
import os
from contextlib import suppress
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

from qiskit_ibm_runtime import SamplerV2

from ..utils import bell
from .dependencies import integration_test_dependencies

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

    from qiskit_ibm_runtime import RuntimeJobV2

    from .dependencies import Dependencies

logger = logging.getLogger(__name__)


@pytest.fixture(scope="class")
def dependencies() -> Dependencies:
    """Return the dependencies of an integration test, from the environment configuration."""
    return integration_test_dependencies()


@pytest.fixture
def submit_bell_job(dependencies: Dependencies) -> Iterator[Callable[..., RuntimeJobV2]]:
    """Return a function that submits a sampler job running a bell circuit.

    The jobs submitted through the returned function are cancelled when the test finishes.
    """
    submitted: list[RuntimeJobV2] = []

    def _submit(backend_name: str | None = None, job_tags: list[str] | None = None) -> RuntimeJobV2:
        """Submit a sampler job running a bell circuit.

        Args:
            backend_name: the name of the backend to use. Defaults to the QPU configured in the
                environment.
            job_tags: optional tags to set on the job.

        Returns:
            The submitted job. The function does not wait for it to complete.
        """
        service = dependencies.service

        logger.debug("Submitting bell job on %s", service.channel)
        backend = service.backend(backend_name or dependencies.qpu)
        pm = generate_preset_pass_manager(optimization_level=1, target=backend.target)

        sampler = SamplerV2(mode=backend)
        if job_tags:
            sampler.options.environment.job_tags = job_tags  # type: ignore[union-attr]
        job = sampler.run([pm.run(bell())])

        logger.info("Runtime job %s submitted.", job.job_id())
        submitted.append(job)

        return job

    yield _submit

    # Cancel submitted jobs.
    for job in submitted:
        with suppress(Exception):
            job.cancel()


@pytest.fixture(autouse=True)
def skip_if_not_production(request: pytest.FixtureRequest) -> None:
    """Skip a test marked with `production` when the service is not a production one.

    The dependencies are resolved lazily, so that the tests without the marker do not require
    the environment configuration.
    """
    if request.node.get_closest_marker("production") is None:
        return

    dependencies = request.getfixturevalue("dependencies")
    if "dev" in dependencies.url or "test" in dependencies.url:
        pytest.skip("Skipping integration test. Not supported on staging.")


@pytest.fixture
def integration_job_tags(request: pytest.FixtureRequest) -> list[str]:
    """Return the tags to assign to the jobs submitted by an integration test.

    Returns the following tags:
    * `case:file.class`
    * `test:test`
    * `ci_run:run_id` (if inside CI)
    * `hash:commit_sha` (if inside CI)
    """
    file_path, *identifier = request.node.nodeid.split("::")
    *class_name, test_name = identifier

    tags = [
        f"case:{'.'.join([Path(file_path).stem, *class_name])}",
        f"test:{test_name}",
    ]

    for prefix, variable in (("ci_run", "GITHUB_RUN_ID"), ("hash", "GITHUB_SHA")):
        if value := os.getenv(variable):
            tags.append(f"{prefix}:{value}")

    return [tag[:86] for tag in tags]
