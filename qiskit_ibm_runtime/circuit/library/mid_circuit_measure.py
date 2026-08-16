# This code is part of Qiskit.
#
# (C) Copyright IBM 2025-2026.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Mid-circuit measurement and reset gates."""

from qiskit.circuit import Instruction


class MidCircuitMeasure(Instruction):
    """Alternative 'named' measurement definition.

    This instruction implements an alternative 'named' measurement definition
    (one classical bit, one quantum bit), whose name can be used to map to a corresponding
    mid-circuit measurement instruction implementation on hardware.
    """

    def __init__(self, name: str = "measure_2", label: str | None = None) -> None:
        if not name.startswith("measure_"):
            raise ValueError(
                "Invalid name for mid-circuit measure instruction. "
                "The provided name must start with `measure_`"
            )

        super().__init__(name, 1, 1, [], label=label)


class MidCircuitReset(Instruction):
    """Alternative 'named' reset definition.

    This instruction implements an alternative 'named' reset definition
    (one quantum bit), whose name can be used to map to a corresponding
    mid-circuit reset instruction implementation on hardware.
    """

    def __init__(self, name: str = "reset_2", label: str | None = None) -> None:
        if not name.startswith("reset_"):
            raise ValueError(
                "Invalid name for mid-circuit reset instruction. "
                "The provided name must start with `reset_`"
            )

        super().__init__(name, 1, 0, [], label=label)


class MeasureReset(Instruction):
    """A reset that exposes the measurement it performs internally.

    This instruction implements a reset operation whose intermediate measurement
    result is captured in a classical bit, making it observable to the user.
    It uses one quantum bit and one classical bit, and its name can be used to
    map to a corresponding hardware-level implementation, and must start with
    ``measure_reset``.

    The semantics are: measure the qubit into the classical bit, then
    conditionally flip the qubit back to ``|0>`` — i.e., a reset whose measurement
    outcome is retained.
    """

    def __init__(self, name: str = "measure_reset", label: str | None = None) -> None:
        if not name.startswith("measure_reset"):
            raise ValueError(
                "Invalid name for MeasureReset instruction. "
                "The provided name must start with `measure_reset`"
            )

        super().__init__(name, 1, 1, [], label=label)
