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

"""Utilities for converting option models."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .environment import EnvironmentOptions
from .execution import ExecutionOptions
from .executor import ExecutorOptions
from .simulator import SimulatorOptions

if TYPE_CHECKING:
    from ..ibm_backend import IBMBackend
    from .estimator import EstimatorOptions
    from .sampler import SamplerOptions


def to_runtime_options(
    options: EnvironmentOptions, backend: IBMBackend, max_execution_time: int | None = None
) -> dict:
    """Convert `EnvironmentOptions` into runtime options.

    Args:
        options: environment options to convert.
        backend: backend to use for runtime options.
        max_execution_time: Maximum execution time in seconds.
    """
    runtime_options = options.model_dump()
    runtime_options["backend"] = backend.name
    runtime_options["instance"] = backend._instance

    # 'options.max_execution_time' is deprecated, and when users set it there, they get a warning.
    # Hence, we make 'max_execution_time' prevail
    if max_execution_time is not None:
        runtime_options["max_execution_time"] = max_execution_time

    return runtime_options


def sampler_option_to_executor_options(options: SamplerOptions) -> ExecutorOptions:
    """Map sampler options to executor options, ignoring all irrelevant fields.

    Returns:
        Mapped executor options.
    """
    executor_options = ExecutorOptions()

    executor_options.environment = EnvironmentOptions(**options.environment.model_dump())
    executor_options.execution = ExecutionOptions(
        **options.execution.model_dump(exclude={"meas_type"})
    )
    executor_options.simulator = SimulatorOptions(**options.simulator.model_dump())
    executor_options.max_execution_time = options.max_execution_time

    if options.experimental:
        executor_options.experimental.update(options.experimental)

        if execution_key := options.experimental.get("execution", {}):
            if execution_key.get("scheduler_timing", False):
                executor_options.execution.scheduler_timing = True
            if execution_key.get("stretch_values", False):
                executor_options.execution.stretch_values = True

    return executor_options


def estimator_options_to_executor_options(options: EstimatorOptions) -> ExecutorOptions:
    """Map EstimatorOptions to ExecutorOptions, ignoring all irrelevant fields.

    Returns:
        Mapped executor options.
    """
    executor_options = ExecutorOptions()

    executor_options.environment = EnvironmentOptions(**options.environment.model_dump())
    executor_options.execution = ExecutionOptions(**options.execution.model_dump())
    executor_options.simulator = SimulatorOptions(**options.simulator.model_dump())
    executor_options.max_execution_time = options.max_execution_time

    if options.experimental:
        executor_options.experimental.update(options.experimental)

    if executor_options.simulator.layer_noise_model is None:
        executor_options.simulator.layer_noise_model = options.resilience.layer_noise_model

    return executor_options
