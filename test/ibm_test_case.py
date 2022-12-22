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

"""Custom TestCase for IBM Provider."""

import os
import copy
import logging
import inspect
import unittest
from contextlib import suppress
from collections import defaultdict
from typing import DefaultDict, Dict

from qiskit_ibm_runtime import QISKIT_IBM_RUNTIME_LOGGER_NAME
from qiskit_ibm_runtime.exceptions import IBMNotAuthorizedError
from qiskit_ibm_runtime import QiskitRuntimeService

from .utils import setup_test_logging
from .decorators import IntegrationTestDependencies, integration_test_setup
from .templates import RUNTIME_PROGRAM, RUNTIME_PROGRAM_METADATA, PROGRAM_PREFIX


class IBMTestCase(unittest.TestCase):
    """Custom TestCase for use with qiskit-ibm-runtime."""

    log: logging.Logger
    dependencies: IntegrationTestDependencies
    service: QiskitRuntimeService
    program_ids: Dict[str, str]

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.log = logging.getLogger(cls.__name__)
        filename = "%s.log" % os.path.splitext(inspect.getfile(cls))[0]
        setup_test_logging(cls.log, filename)
        cls._set_logging_level(logging.getLogger(QISKIT_IBM_RUNTIME_LOGGER_NAME))

    @classmethod
    def _set_logging_level(cls, logger: logging.Logger) -> None:
        """Set logging level for the input logger.

        Args:
            logger: Logger whose level is to be set.
        """
        if logger.level is logging.NOTSET:
            try:
                logger.setLevel(cls.log.level)
            except Exception as ex:  # pylint: disable=broad-except
                logger.warning(
                    'Error while trying to set the level for the "%s" logger to %s. %s.',
                    logger,
                    os.getenv("LOG_LEVEL"),
                    str(ex),
                )
        if not any(
            isinstance(handler, logging.StreamHandler) for handler in logger.handlers
        ):
            logger.addHandler(logging.StreamHandler())
            logger.propagate = False


class IBMIntegrationTestCase(IBMTestCase):
    """Custom integration test case for use with qiskit-ibm-runtime."""

    @classmethod
    @integration_test_setup()
    def setUpClass(cls, dependencies: IntegrationTestDependencies) -> None:
        """Initial class level setup."""
        # pylint: disable=arguments-differ
        super().setUpClass()
        cls.dependencies = dependencies
        cls.service = dependencies.service

    def setUp(self) -> None:
        """Test level setup."""
        super().setUp()
        self.to_delete: DefaultDict = defaultdict(list)
        self.to_cancel: DefaultDict = defaultdict(list)

    def tearDown(self) -> None:
        """Test level teardown."""
        super().tearDown()
        # Delete programs
        service = self.service
        for prog in self.to_delete[service.channel]:
            with suppress(Exception):
                service.delete_program(prog)

        # Cancel and delete jobs.
        for job in self.to_cancel[service.channel]:
            with suppress(Exception):
                job.cancel()
            with suppress(Exception):
                service.delete_job(job.job_id())

    def _upload_program(
        self,
        service: QiskitRuntimeService,
        name: str = None,
        max_execution_time: int = 300,
        data: str = None,
        is_public: bool = False,
    ) -> str:
        """Upload a new program."""
        name = name or PROGRAM_PREFIX
        data = data or RUNTIME_PROGRAM
        metadata = copy.deepcopy(RUNTIME_PROGRAM_METADATA)
        metadata["name"] = name
        metadata["max_execution_time"] = max_execution_time
        metadata["is_public"] = is_public
        program_id = service.upload_program(data=data, metadata=metadata)
        self.to_delete[service.channel].append(program_id)
        return program_id


class IBMIntegrationJobTestCase(IBMIntegrationTestCase):
    """Custom integration test case for job-related tests."""

    @classmethod
    def setUpClass(cls):
        """Initial class level setup."""
        # pylint: disable=arguments-differ
        # pylint: disable=no-value-for-parameter
        super().setUpClass()
        cls._create_default_program()
        cls._find_sim_backends()

    @classmethod
    def tearDownClass(cls) -> None:
        """Class level teardown."""
        super().tearDownClass()
        # Delete default program.
        with suppress(Exception):
            service = cls.service
            service.delete_program(cls.program_ids[service.channel])
            cls.log.debug(
                "Deleted %s program %s",
                service.channel,
                cls.program_ids[service.channel],
            )

    @classmethod
    def _create_default_program(cls):
        """Create a default program."""
        metadata = copy.deepcopy(RUNTIME_PROGRAM_METADATA)
        metadata["name"] = PROGRAM_PREFIX
        cls.program_ids = {}
        cls.sim_backends = {}
        service = cls.service
        try:
            prog_id = service.upload_program(data=RUNTIME_PROGRAM, metadata=metadata)
            cls.log.debug("Uploaded %s program %s", service.channel, prog_id)
            cls.program_ids[service.channel] = prog_id
        except IBMNotAuthorizedError:
            raise unittest.SkipTest("No upload access.")

    @classmethod
    def _find_sim_backends(cls):
        """Find a simulator backend for each service."""
        cls.sim_backends[cls.service.channel] = cls.service.backends(simulator=True)[
            0
        ].name

    def _run_program(
        self,
        service,
        program_id=None,
        iterations=1,
        inputs=None,
        interim_results=None,
        final_result=None,
        callback=None,
        backend=None,
        log_level=None,
        job_tags=None,
        max_execution_time=None,
        session_id=None,
        start_session=False,
        sleep_per_iteration=0,
    ):
        """Run a program."""
        self.log.debug("Running program on %s", service.channel)
        inputs = (
            inputs
            if inputs is not None
            else {
                "iterations": iterations,
                "interim_results": interim_results or {},
                "final_result": final_result or {},
                "sleep_per_iteration": sleep_per_iteration,
            }
        )
        pid = program_id or self.program_ids[service.channel]
        backend_name = (
            backend if backend is not None else self.sim_backends[service.channel]
        )
        options = {
            "backend": backend_name,
            "log_level": log_level,
            "job_tags": job_tags,
            "max_execution_time": max_execution_time,
        }
        job = service.run(
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
