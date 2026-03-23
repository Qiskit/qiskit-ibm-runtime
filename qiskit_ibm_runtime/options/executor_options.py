# This code is part of Qiskit.
#
# (C) Copyright IBM 2025.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Executor options."""

from __future__ import annotations

import warnings
from pydantic.dataclasses import dataclass
from pydantic import Field, model_validator

from .environment_options import LogLevelType

MAX_EXECUTION_TIME_DEPRECATION_MSG = (
    "`max_execution_time` is deprecated as of qiskit_ibm_runtime v0.47.0 and will "
    "be removed in a future release. Use `max_usage` instead."
)


@dataclass
class ExecutionOptions:
    """Low-level execution options."""

    init_qubits: bool = True
    r"""Whether to reset the qubits to the ground state for each shot.
    """

    rep_delay: float | None = None
    r"""The repetition delay. This is the delay between a measurement and
    the subsequent quantum circuit. This is only supported on backends that have
    ``backend.dynamic_reprate_enabled=True``. It must be from the
    range supplied by ``backend.rep_delay_range``.
    Default is given by ``backend.default_rep_delay``.
    """


@dataclass
class EnvironmentOptions:
    """Options related to the execution environment."""

    log_level: LogLevelType = "WARNING"
    r"""logging level to set in the execution environment. The valid
        log levels are: ``DEBUG``, ``INFO``, ``WARNING``, ``ERROR``, and ``CRITICAL``.
    """

    job_tags: list[str] = Field(default_factory=list)
    r"""Tags to be assigned to the job. 
    
    The tags can subsequently be used as a filter in the 
    :meth:`qiskit_ibm_runtime.qiskit_runtime_service.jobs()` function call. 
    """

    private: bool = False
    r"""Boolean that indicates whether the job is marked as private. 
    
    When set to true, 
        input parameters are not returned, and the results can only be read once. 
        After the job is completed, input parameters are deleted from the service. 
        After the results are read, these are also deleted from the service. 
        When set to false, the input parameters and results follow the 
        standard retention behavior of the API.
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

    image: str | None = None
    r"""Runtime image used for this job."""

    @model_validator(mode="after")
    def match_max_execution_time_and_max_usage(self) -> EnvironmentOptions:
        """Validate deprecated usage of `max_execution_time`, in favor of `max_usage`."""
        max_execution_time = self.max_execution_time
        max_usage = self.max_usage

        if max_usage is not None:
            if max_execution_time is not None:
                warnings.warn(
                    f"{MAX_EXECUTION_TIME_DEPRECATION_MSG}. Both have been set to {max_usage}.",
                    DeprecationWarning,
                    stacklevel=2,
                )

            self.max_execution_time = max_usage
        else:
            if max_execution_time is not None:
                warnings.warn(
                    f"{MAX_EXECUTION_TIME_DEPRECATION_MSG}. Both have been set to {max_execution_time}.",
                    DeprecationWarning,
                    stacklevel=2,
                )

                self.max_usage = max_execution_time

        return self


@dataclass
class ExecutorOptions:
    """Options for the executor."""

    environment: EnvironmentOptions = Field(default_factory=EnvironmentOptions)
    """Options related to the execution environment."""

    execution: ExecutionOptions = Field(default_factory=ExecutionOptions)
    """Low-level execution options."""

    experimental: dict = Field(default_factory=dict)
    """Experimental options that are passed to the executor."""
