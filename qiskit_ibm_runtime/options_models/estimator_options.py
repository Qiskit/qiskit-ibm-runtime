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
from typing import Literal

from pydantic import Field
from pydantic.dataclasses import dataclass

from .dynamical_decoupling_options import DynamicalDecouplingOptions
from .environment_options import EnvironmentOptions
from .execution_options import ExecutionOptions
from .executor_options import ExecutorOptions
from .resilience_options import ResilienceOptions
from .simulator_options import SimulatorOptions
from .twirling_options import TwirlingOptions
from .utils import PRIMITIVES_CONFIG


@dataclass(config=PRIMITIVES_CONFIG)
class EstimatorOptions:
    """Options for the executor-based EstimatorV2."""

    default_precision: float = 0.015625
    """The default precision for expectation value estimates if not specified in the PUBs
    or in the run method.

    The default value of ``0.015625``, equivalent to ``4096**-0.5``, represents the precision
    expected from ``4096`` shots in the presence of i.i.d. noise.
    """

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

    See :class:`.ExecutionOptions` for all available options.
    """

    twirling: TwirlingOptions = Field(default_factory=TwirlingOptions)
    """Twirling options.

    Currently only enable_measure=False is supported.

    See :class:`.TwirlingOptions` for all available options.
    """

    dynamical_decoupling: DynamicalDecouplingOptions = Field(
        default_factory=DynamicalDecouplingOptions
    )
    """Dynamical decoupling options.

    See :class:`~.DynamicalDecouplingOptions` for all available options.
    """

    simulator: SimulatorOptions = Field(default_factory=SimulatorOptions)
    """Simulator options.

    See :class:`~.SimulatorOptions` for all available options.
    """

    experimental: dict = Field(default_factory=dict)
    """Experimental options."""

    max_execution_time: int | None = None
    """Maximum execution time in seconds, based on system execution time (not wall clock time)."""

    environment: EnvironmentOptions = Field(default_factory=EnvironmentOptions)
    """Options related to the execution environment."""

    resilience: ResilienceOptions = Field(default_factory=ResilienceOptions)
    """Advanced resilience options to fine-tune the resilience strategy.

    See :class:`.~ResilienceOptions` for all available options.
    """

    resilience_level: Literal[0, 1, 2] = 1
    """How much resilience to build against errors.

    Higher levels generate more accurate results, at the expense of longer processing times.
    The supported values are:
    * 0: No mitigation.
    * 1: Minimal mitigation costs. Mitigate error associated with readout errors.
    * 2: Medium mitigation costs. Typically reduces bias in estimators but is not guaranteed to be
        zero bias.

    Refer to the
    `Configure error mitigation for Qiskit Runtime
    <https://quantum.cloud.ibm.com/docs/guides/configure-error-mitigation>`_ guide
    for more information about the error mitigation methods used at each level.
    """

    def to_executor_options(self) -> ExecutorOptions:
        """Map EstimatorOptions to ExecutorOptions, ignoring all irrelevant fields.

        .. note::
            Simulator options are ignored as executor does not support local mode.

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
