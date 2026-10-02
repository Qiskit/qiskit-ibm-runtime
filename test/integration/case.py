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
from collections import defaultdict
from contextlib import suppress
from typing import TYPE_CHECKING

from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

from qiskit_ibm_runtime import SamplerV2
from test.decorators import integration_test_setup
from test.ibm_test_case import IBMTestCase
from test.utils import bell

if TYPE_CHECKING:
    from qiskit_ibm_runtime import QiskitRuntimeService
    from test.decorators import IntegrationTestDependencies


class IBMIntegrationTestCase(IBMTestCase):
    """Custom integration test case for use with qiskit-ibm-runtime."""

    dependencies: IntegrationTestDependencies
    service: QiskitRuntimeService

    @classmethod
    @integration_test_setup()
    def setUpClass(cls, dependencies: IntegrationTestDependencies) -> None:
        """Initial class level setup."""
        super().setUpClass()
        cls.dependencies = dependencies
        cls.service = dependencies.service

    def setUp(self) -> None:
        """Test level setup."""
        super().setUp()
        self.to_delete: defaultdict = defaultdict(list)
        self.to_cancel: defaultdict = defaultdict(list)

    def tearDown(self) -> None:
        """Test level teardown."""
        super().tearDown()
        service = self.service

        # Cancel and delete jobs.
        for job in self.to_cancel[service.channel]:
            with suppress(Exception):
                job.cancel()


class IBMIntegrationJobTestCase(IBMIntegrationTestCase):
    """Custom integration test case for job-related tests."""

    log: logging.Logger
    program_ids: dict[str, str]
    sim_backends: dict[str, str | None]

    @classmethod
    def setUpClass(cls) -> None:
        """Initial class level setup."""
        super().setUpClass()
        cls.log = logging.getLogger(cls.__name__)
        cls.program_ids = {}
        cls.sim_backends = {}
        service = cls.service
        cls.program_ids[service.channel] = "sampler"
        cls._find_sim_backends()

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

    def _run_program(
        self,
        service,
        program_id=None,
        inputs=None,
        circuits=None,
        callback=None,
        backend=None,
        log_level=None,
        job_tags=None,
        max_execution_time=None,
        session_id=None,
        start_session=False,
    ):
        """Run a program."""
        self.log.debug("Running program on %s", service.channel)
        pid = program_id or self.program_ids[service.channel]
        backend_name = backend if backend is not None else self.sim_backends[service.channel]
        backend = service.backend(backend_name)
        pm = generate_preset_pass_manager(optimization_level=1, target=backend.target)
        inputs = (
            inputs
            if inputs is not None
            else {
                "circuits": pm.run(circuits) if circuits else pm.run(bell()),
            }
        )

        options = {
            "backend": backend_name,
            "log_level": log_level,
            "job_tags": job_tags,
            "max_execution_time": max_execution_time,
        }
        if pid == "sampler":
            sampler = SamplerV2(mode=backend)
            if job_tags:
                sampler.options.environment.job_tags = job_tags
            if circuits:
                job = sampler.run([pm.run(circuits) if circuits else pm.run(bell())])
            else:
                job = sampler.run([pm.run(bell())])
        else:
            job = service._run(
                program_id=pid,
                inputs=inputs,
                options=options,
                session_id=session_id,
                callback=callback,
                start_session=start_session,
            )
        self.log.info("Runtime job %s submitted.", job.job_id())
        self.to_cancel[service.channel].append(job)
        return job
