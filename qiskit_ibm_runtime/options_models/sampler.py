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

from .base import BaseOptionsModel
from .dynamical_decoupling import DynamicalDecouplingOptions
from .environment import SamplerEnvironmentOptions
from .execution import SamplerExecutionOptions
from .simulator import SimulatorOptions
from .twirling import TwirlingOptions


class SamplerOptions(BaseOptionsModel):
    """Options for the executor-based SamplerV2."""

    default_shots: int | None = 4096
    """The default number of shots to use if none are specified in the PUBs or in the run method."""

    dynamical_decoupling: DynamicalDecouplingOptions = DynamicalDecouplingOptions()
    """Suboptions for dynamical decoupling."""

    execution: SamplerExecutionOptions = SamplerExecutionOptions()
    """Execution options."""

    twirling: TwirlingOptions = TwirlingOptions()
    """Pauli twirling options."""

    simulator: SimulatorOptions = SimulatorOptions()
    """Simulator options."""

    experimental: dict = {}
    """Experimental options."""

    max_execution_time: int | None = None
    """Maximum execution time in seconds, based on system execution time (not wall clock time)."""

    environment: SamplerEnvironmentOptions = SamplerEnvironmentOptions()
    """Options related to the execution environment."""
