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

from dataclasses import dataclass, field

from ....options.dynamical_decoupling_options import DynamicalDecouplingOptions
from ....options.twirling_options import TwirlingOptions
from ....options.sampler_execution_options import SamplerExecutionOptionsV2
from ....options.environment_options import EnvironmentOptions
from ....options.simulator_options import SimulatorOptions


@dataclass
class SamplerOptions:
    """Options for the executor-based SamplerV2.

    This class provides the same interface as the old SamplerOptions but is designed
    to work with the executor-based implementation. It reuses the existing option
    sub-classes from qiskit_ibm_runtime.options.

    Args:
        default_shots: The default number of shots to use if none are specified in the
            PUBs or in the run method. Default: 4096.
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
        simulator: Simulator options. See :class:`SimulatorOptions` for all
            available options. Inherited from OptionsV2.
    """

    default_shots: int | None = 4096
    dynamical_decoupling: DynamicalDecouplingOptions = field(
        default_factory=DynamicalDecouplingOptions
    )
    execution: SamplerExecutionOptionsV2 = field(default_factory=SamplerExecutionOptionsV2)
    twirling: TwirlingOptions = field(default_factory=TwirlingOptions)
    experimental: dict | None = None

    # Inherited from OptionsV2
    max_execution_time: int | None = None
    environment: EnvironmentOptions = field(default_factory=EnvironmentOptions)
    simulator: SimulatorOptions = field(default_factory=SimulatorOptions)
