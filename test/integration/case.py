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

"""Custom TestCases for integration tests."""

from __future__ import annotations

import logging
import os
from contextlib import suppress
from dataclasses import dataclass
from typing import TYPE_CHECKING
from unittest import SkipTest

from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2
from test.ibm_test_case import IBMTestCase
from test.utils import bell

if TYPE_CHECKING:
    from qiskit_ibm_runtime.accounts import ChannelType

logger = logging.getLogger(__name__)


@dataclass
class IntegrationTestDependencies:
    """Integration test dependencies."""

    service: QiskitRuntimeService
    instance: str | None
    qpu: str
    token: str
    channel: ChannelType
    url: str


def integration_test_dependencies(init_service: bool = True) -> IntegrationTestDependencies:
    """Return the dependencies of an integration test, from the environment configuration.

    Args:
        init_service: whether to initialize the `QiskitRuntimeService` from the environment
            configuration. When `False`, the returned dependencies have no service.

    Returns:
        The dependencies of an integration test.

    Raises:
        SkipTest: if the environment does not provide a token and a url.
    """
    channel: ChannelType = "ibm_quantum_platform"
    token = os.getenv("QISKIT_IBM_TOKEN")
    url = os.getenv("QISKIT_IBM_URL")
    instance = os.getenv("QISKIT_IBM_INSTANCE")

    if not token or not url:
        raise SkipTest("No integration test credentials available.")

    service = (
        QiskitRuntimeService(channel=channel, token=token, url=url, instance=instance)
        if init_service
        else None
    )

    return IntegrationTestDependencies(
        channel=channel,
        token=token,
        url=url,
        instance=instance,
        qpu=os.getenv("QISKIT_IBM_QPU"),
        service=service,
    )


class IBMIntegrationTestCase(IBMTestCase):
    """Custom integration test case for use with qiskit-ibm-runtime."""

    dependencies: IntegrationTestDependencies
    service: QiskitRuntimeService

    @classmethod
    def setUpClass(cls) -> None:
        """Initial class level setup."""
        super().setUpClass()
        cls.dependencies = integration_test_dependencies()
        cls.service = cls.dependencies.service


class IBMIntegrationJobTestCase(IBMIntegrationTestCase):
    """Custom integration test case for job-related tests."""

    program_ids: dict[str, str]
    sim_backends: dict[str, str | None]

    @classmethod
    def setUpClass(cls) -> None:
        """Initial class level setup."""
        super().setUpClass()
        cls.program_ids = {}
        cls.sim_backends = {}
        service = cls.service
        cls.program_ids[service.channel] = "sampler"
        cls._find_sim_backends()

    def setUp(self) -> None:
        """Test level setup."""
        super().setUp()
        self.to_cancel: list = []

    def tearDown(self) -> None:
        """Test level teardown."""
        super().tearDown()

        # Cancel submitted jobs.
        for job in self.to_cancel:
            with suppress(Exception):
                job.cancel()

    @classmethod
    def _find_sim_backends(cls) -> None:
        """Find a simulator or test backend for each service."""
        backends = cls.service.backends()
        # Simulators or tests backends can be not available
        cls.sim_backends[cls.service.channel] = None
        for backend in backends:
            if backend.name.startswith("test_eagle"):
                cls.sim_backends[cls.service.channel] = backend.name
                break

    def _run_program(self, service, circuits=None, backend=None, job_tags=None):
        """Run a program."""
        logger.debug("Running program on %s", service.channel)
        backend_name = backend if backend is not None else self.sim_backends[service.channel]
        backend = service.backend(backend_name)
        pm = generate_preset_pass_manager(optimization_level=1, target=backend.target)

        sampler = SamplerV2(mode=backend)
        if job_tags:
            sampler.options.environment.job_tags = job_tags
        job = sampler.run([pm.run(circuits) if circuits else pm.run(bell())])

        logger.info("Runtime job %s submitted.", job.job_id())
        self.to_cancel.append(job)
        return job
