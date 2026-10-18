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

"""Tests related to logger setup via ``setup_logger()``."""

import logging
import os
from tempfile import NamedTemporaryFile

import pytest

from qiskit_ibm_runtime.utils.logging import (
    QISKIT_IBM_RUNTIME_LOG_FILE,
    QISKIT_IBM_RUNTIME_LOG_LEVEL,
    setup_logger,
)

from ..account import custom_envs


class TestLogger:
    """Tests related to logger setup via ``setup_logger()``."""

    def test_no_log_level(self, test_id: str) -> None:
        """Test setting up a logger without a log level.

        Note:
            The log level should default to `NOTSET` when no level is specified.
        """
        logger = logging.getLogger(test_id)
        default_level_not_set = logging.NOTSET

        with custom_envs({}):
            if QISKIT_IBM_RUNTIME_LOG_LEVEL in os.environ:
                del os.environ[QISKIT_IBM_RUNTIME_LOG_LEVEL]
            setup_logger(logger)
            assert logger.level == default_level_not_set

    def test_empty_log_level(self, test_id: str) -> None:
        """Test setting up a logger with an empty string log level.

        Note:
            The log level should default to `NOTSET` when an empty string is specified.
        """
        logger = logging.getLogger(test_id)
        default_level_not_set = logging.NOTSET

        with custom_envs({QISKIT_IBM_RUNTIME_LOG_LEVEL: ""}):
            setup_logger(logger)
            assert logger.level == default_level_not_set

    @pytest.mark.parametrize("invalid_log_level", ["invalid", "debugs"])
    def test_invalid_log_level(self, invalid_log_level: str, test_id: str) -> None:
        """Test setting up a logger with invalid log levels, should default to `WARNING`.

        Note:
              The log level should default to `WARNING` when an invalid level is specified.
        """
        logger = logging.getLogger(test_id)
        default_level_invalid = logging.WARNING

        with custom_envs({QISKIT_IBM_RUNTIME_LOG_LEVEL: invalid_log_level}):
            setup_logger(logger)
            assert logger.level == default_level_invalid

    @pytest.mark.parametrize(
        ("level_name", "level_value"),
        [
            ("debug", logging.DEBUG),
            ("iNFo", logging.INFO),
            ("WARNING", logging.WARNING),
            ("error", logging.ERROR),
            ("CRITICAL", logging.CRITICAL),
        ],
    )
    def test_valid_log_levels_mixed_casing(
        self, level_name: str, level_value: int, test_id: str
    ) -> None:
        """Test setting up a logger with all valid levels, case insensitive."""
        logger = logging.getLogger(test_id)

        with custom_envs({QISKIT_IBM_RUNTIME_LOG_LEVEL: level_name}):
            setup_logger(logger)
            assert logger.level == level_value

    @pytest.mark.skipif(os.name == "nt", reason="Test not supported in Windows")
    def test_log_file(self, test_id: str) -> None:
        """Test setting up a logger by specifying a file and log level."""
        logger = logging.getLogger(test_id)
        log_level_error = ("ERROR", logging.ERROR)

        with NamedTemporaryFile() as temp_log_file:
            # Set the environment variables, including the temp file name.
            with custom_envs(
                {
                    QISKIT_IBM_RUNTIME_LOG_LEVEL: log_level_error[0],
                    QISKIT_IBM_RUNTIME_LOG_FILE: temp_log_file.name,
                }
            ):
                setup_logger(logger)

                assert logger.level == log_level_error[1]

                # Assert the file handler was created.
                assert logger.handlers
                assert len(logger.handlers) == 1

                # Note that only messages >= `ERROR` will be logged.
                logger.warning("This is a warning message that should not be logged in the file.")
                logger.error("This is an error message that should be logged in the file.")
                logger.critical("This is a critical message that should be logged in the file.")

                # Assert the file exists.
                log_file_name = os.environ[QISKIT_IBM_RUNTIME_LOG_FILE]
                assert os.path.exists(log_file_name)

                # Assert the messages were logged.
                with open(temp_log_file.name, encoding="utf-8") as file_:
                    content_as_str = file_.read()

                    # Check whether the appropriate substrings are in the file.
                    assert "warning message" not in content_as_str
                    assert "error message" in content_as_str
                    assert "critical message" in content_as_str
