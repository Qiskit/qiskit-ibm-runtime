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

"""Options for the executor-based EstimatorV2."""

from __future__ import annotations
from dataclasses import asdict

from pydantic import Field
from pydantic.dataclasses import dataclass

from .environment_options import EnvironmentOptions
from .twirling_options import TwirlingOptions
from qiskit_ibm_runtime.options_models.executor_options import ExecutorOptions
from qiskit_ibm_runtime.options_models.execution_options import ExecutionOptions
from .utils import PRIMITIVES_CONFIG


@dataclass(config=PRIMITIVES_CONFIG)
class EstimatorOptions:
    """Options for the executor-based EstimatorV2.

    This is a minimal implementation without twirling, dynamical decoupling,
    or error mitigation features.
    """

    default_precision: float = 0.015625
    """The default precision for expectation value estimates if not specified in the PUBs
    or in the run method."""

    default_shots: int | None = None
    """The total number of shots to use per circuit per configuration.

    .. note::
        If set, this value overrides :attr:`~default_precision`.

    A configuration is a combination of a specific parameter value binding set and a
    physical measurement basis. A physical measurement basis groups together some
    collection of qubit-wise commuting observables for some specific circuit/parameter
    value set to create a single measurement with basis rotations that is inserted into
    hardware executions.

    If twirling is enabled, the value of this option will be divided over circuit
    randomizations, with a smaller number of shots per randomization. See the
    :attr:`~twirling` options.
    """

    execution: ExecutionOptions = Field(default_factory=ExecutionOptions)
    """Execution options.

    See :class:`.ExecutionOptions` for all available options."""

    twirling: TwirlingOptions = Field(default_factory=TwirlingOptions)
    """Twirling options.

    Currently only enable_measure=False is supported.

    See :class:`.TwirlingOptions` for all available options."""

    experimental: dict | None = None
    """Experimental options."""

    max_execution_time: int | None = None
    """Maximum execution time in seconds, based on system execution time (not wall clock time)."""

    environment: EnvironmentOptions = Field(default_factory=EnvironmentOptions)
    """Options related to the execution environment."""

    def to_executor_options(self) -> ExecutorOptions:
        """Map EstimatorOptions to ExecutorOptions, ignoring all irrelevant fields.

        Returns:
            Mapped executor options.
        """
        executor_options = ExecutorOptions()

        environment_options = asdict(self.environment)  # type: ignore[call-overload]
        execution_options = asdict(self.execution)  # type: ignore[call-overload]
        executor_options.environment = EnvironmentOptions(**environment_options)
        executor_options.execution = ExecutionOptions(**execution_options)

        executor_options.environment.max_execution_time = self.max_execution_time
        if self.experimental:
            executor_options.environment.image = self.experimental.get("image", None)
            executor_options.experimental.update(self.experimental)

        return executor_options
