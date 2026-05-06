# This code is part of Qiskit.
#
# (C) Copyright IBM 2022-2026.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Options related to the execution environment."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, model_validator
from pydantic.dataclasses import dataclass

from ..options.utils import match_max_execution_time_and_max_usage

from .utils import PRIMITIVES_CONFIG

LogLevelType = Literal[
    "DEBUG",
    "INFO",
    "WARNING",
    "ERROR",
    "CRITICAL",
]


@dataclass(config=PRIMITIVES_CONFIG)
class EnvironmentOptions:
    """Options related to the execution environment."""

    log_level: LogLevelType = "WARNING"
    """logging level to set in the execution environment.

    The valid log levels are: ``DEBUG``, ``INFO``, ``WARNING``, ``ERROR``, and ``CRITICAL``.
    """

    job_tags: list[str] = Field(default_factory=list)
    """Tags to be assigned to the job.

    The tags can subsequently be used as a filter in the
    :meth:`qiskit_ibm_runtime.qiskit_runtime_service.jobs()` function call.
    """

    private: bool = False
    """Boolean that indicates whether the job is marked as private.

    When set to true, input parameters are not returned, and the results can only be read once.
    After the job is completed, input parameters are deleted from the service. After the results are
    read, these are also deleted from the service. When set to false, the input parameters and
    results follow the standard retention behavior of the API.
    """

    max_execution_time: int | None = None
    """Maximum execution time in seconds.

    This value bounds system execution time (not wall clock time). System execution time is the
    amount of time that the system is dedicated to processing your job. If a job exceeds
    this time limit, it is forcibly cancelled.
    """

    max_usage: int | None = None
    """Maximum usage in seconds.

    This value bounds system usage (not wall clock time). System usage is the amount of time that
    the system is dedicated to processing your job. If a job exceeds this time limit, it is
    forcibly cancelled.
    """

    image: (
        Annotated[
            str,
            Field(
                pattern="[a-zA-Z0-9]+([/.\\-_][a-zA-Z0-9]+)*:[a-zA-Z0-9]+([.\\-_][a-zA-Z0-9]+)*$",
            ),
        ]
        | None
    ) = None
    """Runtime image used for this job."""

    @model_validator(mode="after")
    def match_max_execution_time_and_max_usage(self) -> EnvironmentOptions:
        """Validate deprecated usage of `max_execution_time`, in favor of `max_usage`."""
        return match_max_execution_time_and_max_usage(self)
