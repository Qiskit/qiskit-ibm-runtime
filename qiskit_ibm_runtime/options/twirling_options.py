# This code is part of Qiskit.
#
# (C) Copyright IBM 2023.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Twirling options."""

from typing import Literal, Union

from pydantic.dataclasses import dataclass as pydantic_dataclass
from pydantic import model_validator, ConfigDict

from .utils import Unset, UnsetType


TwirlingStrategyType = Literal[
    "active",
    "active-accum",
    "active-circuit",
    "all",
]


@pydantic_dataclass(config=ConfigDict(validate_assignment=True, arbitrary_types_allowed=True, extra="forbid"))
class TwirlingOptions:
    """Twirling options.

    Args:
        gates: Whether to apply 2-qubit gate twirling.
            By default, gate twirling is enabled for resilience level >0.

        measure: Whether to apply measurement twirling.
            By default, measurement twirling is enabled for resilience level >0.

        strategy: Specify the strategy of twirling qubits in identified layers of
            2-qubit twirled gates. Allowed values are

            - If ``"active"`` only the instruction qubits in each individual twirled
              layer will be twirled.
            - If ``"active-circuit"`` the union of all instruction qubits in the circuit
              will be twirled in each twirled layer.
            - If ``"active-accum"`` the union of instructions qubits in the circuit up to
              the current twirled layer will be twirled in each individual twirled layer.
            - If ``"all"`` all qubits in the input circuit will be twirled in each
              twirled layer.
            - If None twirling will be disabled.

            Default: ``"active-accum"`` for resilience levels 0, 1, 2. ``"active"`` for
                     resilience level 3.
    """

    gates: Union[UnsetType, bool] = Unset
    measure: Union[UnsetType, bool] = Unset
    strategy: Union[UnsetType, TwirlingStrategyType] = Unset

    # @model_validator(mode='after')
    # def _validate_options(self):
    #     """Validate the model."""
    #     if self.gates is not True:
    #         self.strategy = Unset

    #     return self
