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

from typing import Literal

from dataclasses import asdict
from pydantic import Field
from pydantic.dataclasses import dataclass

from .dynamical_decoupling_options import DynamicalDecouplingOptions
from .twirling_options import TwirlingOptions
from .environment_options import EnvironmentOptions
from ....options.executor_options import ExecutorOptions

from ....options.executor_options import ExecutionOptions


@dataclass
class SamplerExecutionOptions(ExecutionOptions):
    """Execution options for the sampler primitive.

    Args:
        init_qubits: Whether to reset the qubits to the ground state for each shot.
            Inherited from :class:`ExecutionOptions`.
        rep_delay: The repetition delay. Inherited from :class:`ExecutionOptions`.
        meas_type: How to process and return measurement results. This option sets
            the return type of all classical registers in all sampler pub results.

            * ``"classified"``: Returns a BitArray with classified measurement outcomes.
            * ``"kerneled"``: Returns complex IQ data points from kerneling the measurement
              trace, in arbitrary units.
            * ``"avg_kerneled"``: Returns complex IQ data points averaged over shots,
              in arbitrary units.
    """

    meas_type: Literal["classified", "kerneled", "avg_kerneled"] = "classified"

    def to_executor_execution_options(self) -> ExecutionOptions:
        """Convert to execution options.

        This drops the `meas_type` field, which is passed as part of the QuantumProgram."""
        fields = asdict(self)
        fields.pop("meas_type")
        return ExecutionOptions(**fields)


@dataclass
class SamplerOptions:
    """Options for the executor-based SamplerV2.

    Args:
        default_shots: The default number of shots to use if none are specified in the
            PUBs or in the run method.
        dynamical_decoupling: Suboptions for dynamical decoupling. See
            :class:`DynamicalDecouplingOptions` for all available options.
        execution: Execution time options. See :class:`SamplerExecutionOptionsV2`
            for all available options.
        twirling: Pauli twirling options. See :class:`TwirlingOptions` for all
            available options.
        experimental: Experimental options as a dictionary.
        max_execution_time: Maximum execution time in seconds, based on system
            execution time (not wall clock time). Inherited from OptionsV2.
        environment: Options related to the execution environment. See
            :class:`EnvironmentOptions` for all available options. Inherited from OptionsV2.
    """

    default_shots: int | None = 4096
    dynamical_decoupling: DynamicalDecouplingOptions = Field(
        default_factory=DynamicalDecouplingOptions
    )
    execution: SamplerExecutionOptions = Field(default_factory=SamplerExecutionOptions)
    twirling: TwirlingOptions = Field(default_factory=TwirlingOptions)
    experimental: dict | None = None

    max_execution_time: int | None = None
    environment: EnvironmentOptions = Field(default_factory=EnvironmentOptions)

    def to_executor_options(self) -> ExecutorOptions:
        """Map SamplerOptions to ExecutorOptions.

        Returns:
            ExecutorOptions: Mapped executor options.
        """
        executor_options = ExecutorOptions()

        # Map execution options
        executor_options.execution = self.execution.to_executor_execution_options()

        # Map environment options
        executor_options.environment = self.environment.to_executor_environment_options()

        if (max_exec_time := self.max_execution_time) is not None:
            executor_options.environment.max_execution_time = max_exec_time

        if self.experimental is not None and "image" in self.experimental:
            executor_options.environment.image = self.experimental["image"]

        return executor_options
