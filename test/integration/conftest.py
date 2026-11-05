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
from contextlib import suppress
from typing import TYPE_CHECKING

import pytest
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

from qiskit_ibm_runtime import SamplerV2

from ..utils import bell
from .dependencies import integration_test_dependencies

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

    from qiskit_ibm_runtime import RuntimeJobV2
    from qiskit_ibm_runtime.ibm_backend import IBMBackend

    from .dependencies import Dependencies

logger = logging.getLogger(__name__)


@pytest.fixture(scope="class")
def dependencies() -> Dependencies:
    """Return the dependencies of an integration test, from the environment configuration."""
    return integration_test_dependencies()


@pytest.fixture(scope="class")
def backend_test(dependencies: Dependencies) -> IBMBackend | None:
    """Return the test backend used by the tests in the class, from the environment config."""
    for backend in dependencies.service.backends():
        if backend.name.startswith("test_eagle"):
            return backend

    return None


@pytest.fixture
def submit_bell_job(
    dependencies: Dependencies, backend_test: IBMBackend | None
) -> Iterator[Callable[..., RuntimeJobV2]]:
    """Return a function that submits a sampler job running a bell circuit.

    The jobs submitted through the returned function are cancelled when the test finishes.
    """
    submitted: list[RuntimeJobV2] = []

    def _submit(backend_name: str | None = None, job_tags: list[str] | None = None) -> RuntimeJobV2:
        """Submit a sampler job running a bell circuit.

        Args:
            backend_name: the name of the backend to use. Defaults to the test backend.
            job_tags: optional tags to set on the job.

        Returns:
            The submitted job. The function does not wait for it to complete.
        """
        service = dependencies.service

        logger.debug("Submitting bell job on %s", service.channel)
        backend = service.backend(backend_name) if backend_name else backend_test
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
