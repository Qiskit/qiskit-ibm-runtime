# This code is part of Qiskit.
#
# (C) Copyright IBM 2022.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Estimator options."""

from typing import Union

from pydantic import Field

from .utils import (
    Dict,
    Unset,
    UnsetType,
)
from .execution_options import ExecutionOptionsV2
from .resilience_options import ResilienceOptionsV2
from .twirling_options import TwirlingOptions
from .dynamical_decoupling_options import DynamicalDecouplingOptions
from .options import OptionsV2
from .utils import primitive_dataclass, make_constraint_validator

MAX_RESILIENCE_LEVEL: int = 2


@primitive_dataclass
class EstimatorOptions(OptionsV2):
    """Options for V2 Estimator."""

    # Sadly we cannot use pydantic's built in validation because it won't work on Unset.
    default_precision: Union[UnsetType, float] = Unset
    r"""The default precision to use for any PUB or ``run()``
        call that does not specify one.
        Each Estimator PUB can specify its own precision. If the ``run()`` method
        is given a precision, then that value is used for all PUBs in the ``run()``
        call that do not specify their own. 
        
        Default: 0.015625 (1 / sqrt(4096)).
    """
    default_shots: Union[UnsetType, int, None] = Unset
    r"""The total number of shots to use per circuit per configuration.

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

        Default: ``None``.
    """
    resilience_level: Union[UnsetType, int] = Unset
    r"""How much resilience to build against errors.
        Higher levels generate more accurate results,
        at the expense of longer processing times.

        * 0: No mitigation.
        * 1: Minimal mitigation costs. Mitigate error associated with readout errors.
        * 2: Medium mitigation costs. Typically reduces bias in estimators but
          is not guaranteed to be zero bias.

        Refer to the
        `Configure error mitigation for Qiskit Runtime
        <https://quantum.cloud.ibm.com/docs/guides/configure-error-mitigation>`_ guide
        for more information about the error mitigation methods used at each level.

        Default: 1.
    """
    seed_estimator: Union[UnsetType, int] = Unset
    r"""Seed used to control sampling. 
    
        Default: ``None``.
    """
    dynamical_decoupling: Union[DynamicalDecouplingOptions, Dict] = Field(
        default_factory=DynamicalDecouplingOptions
    )
    r"""Suboptions for dynamical decoupling. See
        :class:`DynamicalDecouplingOptions` for all available options.
    """
    resilience: Union[ResilienceOptionsV2, Dict] = Field(default_factory=ResilienceOptionsV2)
    r"""Advanced resilience options to fine-tune the resilience strategy.
        See :class:`ResilienceOptionsV2` for all available options.
    """
    execution: Union[ExecutionOptionsV2, Dict] = Field(default_factory=ExecutionOptionsV2)
    r"""Execution time options. See :class:`ExecutionOptionsV2` for all available options.
    """
    twirling: Union[TwirlingOptions, Dict] = Field(default_factory=TwirlingOptions)
    r"""
    Pauli twirling options. See :class:`TwirlingOptions` for all available options.
    """
    experimental: Union[UnsetType, dict] = Unset
    r"""Experimental options. These options are subject to change without notification, and
        stability is not guaranteed.
    """

    _gt0 = make_constraint_validator("default_precision", gt=0)
    _ge0 = make_constraint_validator("default_shots", ge=0)
    _res_lvl = make_constraint_validator("resilience_level", ge=0, le=MAX_RESILIENCE_LEVEL)
