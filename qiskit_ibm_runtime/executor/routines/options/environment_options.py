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

"""Options related to the execution environment."""

from __future__ import annotations

from typing import Literal

from pydantic import Field
from pydantic.dataclasses import dataclass

from ....options.executor_options import EnvironmentOptions as ExecutorEnvironmentOptions


@dataclass
class EnvironmentOptions:
    """Options related to the execution environment."""

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "WARNING"
    """Logging level to set in the execution environment. The valid
    log levels are: ``DEBUG``, ``INFO``, ``WARNING``, ``ERROR``, and ``CRITICAL``."""

    job_tags: list[str] = Field(default_factory=list)
    """Tags to be assigned to the job. The tags can subsequently be used
    as a filter in job queries."""

    private: bool = False
    """Whether the job is marked as private. When set to ``True``,
    input parameters are not returned, and the results can only be read once.
    After the job is completed, input parameters are deleted from the service.
    After the results are read, these are also deleted from the service.
    When set to ``False``, the input parameters and results follow the
    standard retention behavior of the API."""

    def to_executor_options(self) -> ExecutorEnvironmentOptions:
        """Converts the environment options to executor environment options."""
        return ExecutorEnvironmentOptions(
            log_level=self.log_level,
            job_tags=self.job_tags,
            private=self.private,
        )
