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

"""Twirling options."""

from __future__ import annotations

from typing import Literal

from pydantic.dataclasses import dataclass


@dataclass
class TwirlingOptions:
    """Twirling options."""

    enable_gates: bool = False
    """Whether to apply 2-qubit Clifford gate twirling."""

    enable_measure: bool | None = None
    """Whether to enable twirling of measurement instructions.
    Twirling is only applied to measurements that are not involved in a
    conditional block. The default value depends on the primitive:
    ``True`` for Estimator, ``False`` for Sampler.
    """
    num_randomizations: int | Literal["auto"] = "auto"
    """The number of random samples to use when twirling or
    performing sampled mitigation. If ``"auto"``, the value is determined
    automatically based on the input PUB and other options."""

    shots_per_randomization: int | Literal["auto"] = "auto"
    """The number of shots to run for each random sample.
    If ``"auto"``, the value is determined automatically based on the input
    PUB and other options.
    """

    strategy: Literal["active", "active-accum", "active-circuit", "all"] = "active-accum"
    """Specify the strategy of twirling qubits in identified layers of
    2-qubit twirled gates.

      * ``"active"``: Only the instruction qubits in each individual twirled
        layer will be twirled.
      * ``"active-circuit"``: The union of all instruction qubits in the circuit
        will be twirled in each twirled layer.
      * ``"active-accum"``: The union of instructions qubits in the circuit up to
        the current twirled layer will be twirled in each individual twirled layer.
      * ``"all"``: All qubits in the input circuit will be twirled in each
        twirled layer.
    """
