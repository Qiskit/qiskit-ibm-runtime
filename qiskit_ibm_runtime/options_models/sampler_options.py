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

"""Options for the executor-based SamplerV2."""

from __future__ import annotations

from dataclasses import asdict

from pydantic import Field
from pydantic.dataclasses import dataclass

from .dynamical_decoupling_options import DynamicalDecouplingOptions
from .environment_options import EnvironmentOptions, SamplerEnvironmentOptions
from .execution_options import ExecutionOptions, SamplerExecutionOptions
from .executor_options import ExecutorOptions
from .twirling_options import TwirlingOptions
from .utils import PRIMITIVES_CONFIG


@dataclass(config=PRIMITIVES_CONFIG)
class SamplerOptions:
    """Options for the executor-based SamplerV2."""

    default_shots: int | None = 4096
    """The default number of shots to use if none are specified in the PUBs or in the run method."""

    dynamical_decoupling: DynamicalDecouplingOptions = Field(
        default_factory=DynamicalDecouplingOptions
    )
    """Suboptions for dynamical decoupling.

    See :class:`~.DynamicalDecouplingOptions` for all available options.
    """

    execution: SamplerExecutionOptions = Field(default_factory=SamplerExecutionOptions)
    """Execution options.

    See :class:`~.SamplerExecutionOptions` for all available options."""

    twirling: TwirlingOptions = Field(default_factory=TwirlingOptions)
    """Pauli twirling options.

    See :class:`~.TwirlingOptions` for all available options.
    """

    experimental: dict | None = None
    """Experimental options."""

    max_execution_time: int | None = None
    """Maximum execution time in seconds, based on system execution time (not wall clock time).
    """

    environment: SamplerEnvironmentOptions = Field(default_factory=SamplerEnvironmentOptions)
    """Options related to the execution environment."""

    def to_executor_options(self) -> ExecutorOptions:
        """Map sampler options to executor options, ignoring all irrelevant fields.

        Returns:
            Mapped executor options.
        """
        executor_options = ExecutorOptions()

        environment_options = asdict(self.environment)  # type: ignore[call-overload]
        execution_options = asdict(self.execution)  # type: ignore[call-overload]
        execution_options.pop("meas_type")
        executor_options.environment = EnvironmentOptions(**environment_options)
        executor_options.execution = ExecutionOptions(**execution_options)

        executor_options.environment.max_execution_time = self.max_execution_time
        if self.experimental:
            executor_options.environment.image = self.experimental.get("image", None)
            executor_options.experimental.update(self.experimental)

        return executor_options
