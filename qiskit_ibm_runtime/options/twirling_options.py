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

from typing import Optional, Literal, get_args
from dataclasses import dataclass

from .utils import _flexible


TwirlingStrategyType = Literal[
    None,
    "active",
    "active-accum",
    "active-circuit",
    "all",
]


@_flexible
@dataclass
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

    gates: bool = None
    measure: bool = None
    strategy: TwirlingStrategyType = None

    @staticmethod
    def validate_twirling_options(twirling_options: dict) -> None:
        """Validate that twirling options are legal.

        Raises:
            ValueError: if any resilience option is not supported
            ValueError: if noise_amplifier is not in NoiseAmplifierType.
            ValueError: if extrapolator is not in ExtrapolatorType.
            ValueError: if extrapolator == "QuarticExtrapolator" and number of noise_factors < 5.
            ValueError: if extrapolator == "CubicExtrapolator" and number of noise_factors < 4.
        """
        if twirling_options.get("gates"):
            strategy = twirling_options.get("strategy")
            if strategy not in get_args(TwirlingStrategyType):
                raise ValueError(
                    f"Unsupported value {strategy} for twirling strategy. "
                    f"Supported values are {get_args(TwirlingStrategyType)}"
                )
