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
from pydantic import ConfigDict

from .utils import Unset, UnsetType

# TODO use real base options when available
from ..qiskit.primitives.options import primitive_dataclass


TwirlingStrategyType = Literal[
    "active",
    "active-accum",
    "active-circuit",
    "all",
]


@primitive_dataclass
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
