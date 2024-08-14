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
import logging
import inspect
import warnings
from unittest import TestCase
from unittest.util import safe_repr
from contextlib import suppress
from collections import defaultdict
from typing import DefaultDict, Dict

from qiskit_ibm_runtime import QISKIT_IBM_RUNTIME_LOGGER_NAME
from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2

from .utils import setup_test_logging, bell
from .decorators import IntegrationTestDependencies, integration_test_setup


class IBMTestCase(TestCase):
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
        # fail test on deprecation warnings from qiskit
        warnings.filterwarnings("error", category=DeprecationWarning, module=r"^qiskit$")

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
        if not any(isinstance(handler, logging.StreamHandler) for handler in logger.handlers):
            logger.addHandler(logging.StreamHandler())
            logger.propagate = False

    def assert_dict_almost_equal(
        self, dict1, dict2, delta=None, msg=None, places=None, default_value=0
    ):
        """Assert two dictionaries with numeric values are almost equal.

        Fail if the two dictionaries are unequal as determined by
        comparing that the difference between values with the same key are
        not greater than delta (default 1e-8), or that difference rounded
        to the given number of decimal places is not zero. If a key in one
        dictionary is not in the other the default_value keyword argument
        will be used for the missing value (default 0). If the two objects
        compare equal then they will automatically compare almost equal.

        Args:
            dict1 (dict): a dictionary.
            dict2 (dict): a dictionary.
            delta (number): threshold for comparison (defaults to 1e-8).
            msg (str): return a custom message on failure.
            places (int): number of decimal places for comparison.
            default_value (number): default value for missing keys.

        Raises:
            TypeError: if the arguments are not valid (both `delta` and
                `places` are specified).
            AssertionError: if the dictionaries are not almost equal.
        """

        error_msg = self.dicts_almost_equal(dict1, dict2, delta, places, default_value)

        if error_msg:
            msg = self._formatMessage(msg, error_msg)
            raise self.failureException(msg)

    def dicts_almost_equal(self, dict1, dict2, delta=None, places=None, default_value=0):
        """Test if two dictionaries with numeric values are almost equal.

        Fail if the two dictionaries are unequal as determined by
        comparing that the difference between values with the same key are
        not greater than delta (default 1e-8), or that difference rounded
        to the given number of decimal places is not zero. If a key in one
        dictionary is not in the other the default_value keyword argument
        will be used for the missing value (default 0). If the two objects
        compare equal then they will automatically compare almost equal.

        Args:
            dict1 (dict): a dictionary.
            dict2 (dict): a dictionary.
            delta (number): threshold for comparison (defaults to 1e-8).
            places (int): number of decimal places for comparison.
            default_value (number): default value for missing keys.

        Raises:
            TypeError: if the arguments are not valid (both `delta` and
                `places` are specified).

        Returns:
            String: Empty string if dictionaries are almost equal. A description
                of their difference if they are deemed not almost equal.
        """

        def valid_comparison(value):
            """compare value to delta, within places accuracy"""
            if places is not None:
                return round(value, places) == 0
            else:
                return value < delta

        # Check arguments.
        if dict1 == dict2:
            return ""
        if places is not None:
            if delta is not None:
                raise TypeError("specify delta or places not both")
            msg_suffix = " within %s places" % places
        else:
            delta = delta or 1e-8
            msg_suffix = " within %s delta" % delta

        # Compare all keys in both dicts, populating error_msg.
        error_msg = ""
        for key in set(dict1.keys()) | set(dict2.keys()):
            val1 = dict1.get(key, default_value)
            val2 = dict2.get(key, default_value)
            if not valid_comparison(abs(val1 - val2)):
                error_msg += f"({safe_repr(key)}: {safe_repr(val1)} != {safe_repr(val2)}), "

        if error_msg:
            return error_msg[:-2] + msg_suffix
        else:
            return ""


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
        service = self.service

        # Cancel and delete jobs.
        for job in self.to_cancel[service.channel]:
            with suppress(Exception):
                job.cancel()
            with suppress(Exception):
                service.delete_job(job.job_id())


class IBMIntegrationJobTestCase(IBMIntegrationTestCase):
    """Custom integration test case for job-related tests."""

    @classmethod
    def setUpClass(cls):
        """Initial class level setup."""
        # pylint: disable=arguments-differ
        # pylint: disable=no-value-for-parameter
        super().setUpClass()
        cls.program_ids = {}
        cls.sim_backends = {}
        service = cls.service
        cls.program_ids[service.channel] = "sampler"
        cls._find_sim_backends()

    @classmethod
    def tearDownClass(cls) -> None:
        """Class level teardown."""
        super().tearDownClass()

    @classmethod
    def _find_sim_backends(cls):
        """Find a simulator backend for each service."""
        cls.sim_backends[cls.service.channel] = cls.service.backends(simulator=True)[0].name

    def _run_program(
        self,
        service,
        program_id=None,
        inputs=None,
        interim_results=None,
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
        inputs = (
            inputs
            if inputs is not None
            else {
                "interim_results": interim_results or {},
                "circuits": circuits or bell(),
            }
        )
        pid = program_id or self.program_ids[service.channel]
        backend_name = backend if backend is not None else self.sim_backends[service.channel]
        options = {
            "backend": backend_name,
            "log_level": log_level,
            "job_tags": job_tags,
            "max_execution_time": max_execution_time,
        }
        if pid == "sampler":
            backend = service.backend(backend_name)
            sampler = SamplerV2(backend=backend)
            if job_tags:
                sampler.options.environment.job_tags = job_tags
            if circuits:
                job = sampler.run([circuits])
            else:
                job = sampler.run([bell()])
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
