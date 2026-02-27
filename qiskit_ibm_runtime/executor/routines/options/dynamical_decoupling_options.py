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

"""Options for dynamical decoupling."""

from __future__ import annotations

from typing import Literal

from pydantic.dataclasses import dataclass


@dataclass
class DynamicalDecouplingOptions:
    """Options for dynamical decoupling (DD)."""

    enable: bool = False
    """Whether to enable DD as specified by the other options in this class."""

    sequence_type: Literal["XX", "XpXm", "XY4"] = "XX"
    """Which dynamical decoupling sequence to use.

    * ``"XX"``: use the sequence ``tau/2 - (+X) - tau - (+X) - tau/2``
    * ``"XpXm"``: use the sequence ``tau/2 - (+X) - tau - (-X) - tau/2``
    * ``"XY4"``: use the sequence ``tau/2 - (+X) - tau - (+Y) - tau (-X) - tau - (-Y) - tau/2``
    """

    extra_slack_distribution: Literal["middle", "edges"] = "middle"
    """Where to put extra timing delays due to rounding issues.
    
    Rounding issues arise because the discrete time step ``dt`` of the system cannot
    be divided.

    * ``"middle"``: Put the extra slack to the interval at the middle of the sequence.
    * ``"edges"``: Divide the extra slack as evenly as possible into intervals at beginning
        and end of the sequence.
    """

    scheduling_method: Literal["alap", "asap"] = "alap"
    """Whether to schedule gates as soon as ("asap") or as late as ("alap") possible."""

    skip_reset_qubits: bool = False
    """Whether to insert DD on idle periods that immediately follow initialized/reset qubits.
    Since qubits in the ground state are less susceptible to decoherence, it can be beneficial
    to let them be while they are known to be in this state.
    """
