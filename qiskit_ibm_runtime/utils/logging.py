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

"""Logging related functionality."""

import logging
import os

# Constants used by the IBM Quantum logger.

QISKIT_IBM_RUNTIME_LOGGER_NAME = "qiskit_ibm_runtime"
"""The name of the IBM Quantum logger."""

QISKIT_IBM_RUNTIME_LOG_LEVEL = "QISKIT_IBM_RUNTIME_LOG_LEVEL"
"""The environment variable name that is used to set the level for the IBM Quantum logger."""

QISKIT_IBM_RUNTIME_LOG_FILE = "QISKIT_IBM_RUNTIME_LOG_FILE"
"""The environment variable name that is used to set the file for the IBM Quantum logger."""


def setup_logger(logger: logging.Logger) -> None:
    """Setup the logger for the runtime modules with the appropriate level.

    It involves:
        * Use the `QISKIT_IBM_RUNTIME_LOG_LEVEL` environment variable to
          determine the log level to use for the runtime modules. If an invalid
          level is set, the log level defaults to ``WARNING``. The valid log levels
          are ``DEBUG``, ``INFO``, ``WARNING``, ``ERROR``, and ``CRITICAL``
          (case-insensitive). If the environment variable is not set, then the parent
          logger's level is used, which also defaults to `WARNING`.
        * Use the `QISKIT_IBM_RUNTIME_LOG_FILE` environment variable to specify the
          filename to use when logging messages. If a log file is specified, the log
          messages will not be logged to the screen. If a log file is not specified,
          the log messages will only be logged to the screen and not to a file.
    """
    log_level = os.getenv("QISKIT_IBM_RUNTIME_LOG_LEVEL", "")
    log_file = os.getenv("QISKIT_IBM_RUNTIME_LOG_FILE", "")

    # Setup the formatter for the log messages.
    log_fmt = "%(module)s.%(funcName)s:%(levelname)s:%(asctime)s: %(message)s"
    formatter = logging.Formatter(log_fmt)

    # Set propagate to `False` since handlers are to be attached.
    logger.propagate = False

    # Log messages to a file (if specified), otherwise log to the screen (default).
    if log_file:
        # Setup the file handler.
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    else:
        # Setup the stream handler, for logging to console, with the given format.
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)

    # Set the logging level after formatting, if specified.
    if log_level:
        # Default to `WARNING` if the specified level is not valid.
        level = logging.getLevelName(log_level.upper())
        if not isinstance(level, int):
            logger.warning(
                '"%s" is not a valid log level. The valid log levels are: '
                "`DEBUG`, `INFO`, `WARNING`, `ERROR`, and `CRITICAL`.",
                log_level,
            )
            level = logging.WARNING
        logger.debug('The logger is being set to level "%s"', level)
        logger.setLevel(level)
