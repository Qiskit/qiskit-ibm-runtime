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
import time
from functools import partialmethod

from qiskit.test.base import BaseQiskitTestCase

from qiskit_ibm_runtime import QISKIT_IBM_RUNTIME_LOGGER_NAME
from qiskit_ibm_runtime.api.clients.account import AccountClient
from qiskit_ibm_runtime.apiconstants import ApiJobStatus, API_JOB_FINAL_STATES

from .utils import setup_test_logging


class IBMTestCase(BaseQiskitTestCase):
    """Custom TestCase for use with the Qiskit IBM Runtime."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.log = logging.getLogger(cls.__name__)
        filename = '%s.log' % os.path.splitext(inspect.getfile(cls))[0]
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
                    logger, os.getenv('LOG_LEVEL'), str(ex))
        if not any(isinstance(handler, logging.StreamHandler) for handler in logger.handlers):
            logger.addHandler(logging.StreamHandler())
            logger.propagate = False

    def setUp(self) -> None:
        """Test level setup."""
        super().setUp()

    def tearDown(self) -> None:
        """Test level tear down."""
        super().tearDown()
