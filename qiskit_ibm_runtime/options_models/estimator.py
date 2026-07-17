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

from typing import Literal

from .base import BaseOptionsModel
from .dynamical_decoupling import DynamicalDecouplingOptions
from .environment import EnvironmentOptions
from .execution import ExecutionOptions
from .resilience import ResilienceOptions
from .simulator import SimulatorOptions
from .twirling import TwirlingOptions


class EstimatorOptions(BaseOptionsModel):
    """Options for the executor-based EstimatorV2."""

    default_precision: float = 0.015625
    """The default precision to use for any PUB or ``run()`` call that does not specify one.

    The default precision for expectation value estimates if not specified in the PUBs
    or in the run method.

    The default value of ``0.015625``, equivalent to ``4096**-0.5``, represents the precision
    expected from ``4096`` shots in the presence of i.i.d. noise.
    """

    default_shots: int | None = None
    """The total number of shots to use per circuit per configuration.

    .. note::
        If set, this value overrides :attr:`~default_precision`.

    A configuration is a combination of a specific parameter value binding set and a physical
    measurement basis. A physical measurement basis groups together some collection of qubit-wise
    commuting observables for some specific circuit/parameter value set to create a single
    measurement with basis rotations that is inserted into hardware executions.

    If twirling is enabled, the value of this option will be divided over circuit randomizations,
    with a smaller number of shots per randomization. See the :attr:`~twirling` options.
    """

    execution: ExecutionOptions = ExecutionOptions()
    """Execution options."""

    twirling: TwirlingOptions = TwirlingOptions()
    """Twirling options.

    Currently only ``enable_measure=False`` is supported.
    """

    dynamical_decoupling: DynamicalDecouplingOptions = DynamicalDecouplingOptions()
    """Dynamical decoupling options."""

    simulator: SimulatorOptions = SimulatorOptions()
    """Simulator options."""

    experimental: dict = {}
    """Experimental options."""

    max_execution_time: int | None = None
    """Maximum execution time in seconds, based on system execution time (not wall clock time)."""

    environment: EnvironmentOptions = EnvironmentOptions()
    """Options related to the execution environment."""

    resilience: ResilienceOptions = ResilienceOptions()
    """Advanced resilience options to fine-tune the resilience strategy."""

    resilience_level: Literal[0, 1, 2] = 1
    """How much resilience to build against errors.

    Higher levels generate more accurate results, at the expense of longer processing times. The
    supported values are:
    * 0: No mitigation.
    * 1: Minimal mitigation costs. Mitigate error associated with readout errors.
    * 2: Medium mitigation costs. Typically reduces bias in estimators but is not guaranteed to be
        zero bias.

    Refer to the
    `Configure error mitigation for Qiskit Runtime
    <https://quantum.cloud.ibm.com/docs/guides/configure-error-mitigation>`_ guide for more
    information about the error mitigation methods used at each level.
    """
