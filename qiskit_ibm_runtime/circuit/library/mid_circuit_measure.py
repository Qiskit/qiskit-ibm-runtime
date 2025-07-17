# This code is part of Qiskit.
#
# (C) Copyright IBM 2025.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""MidCircuitMeasure gate."""

from qiskit.circuit import Instruction


class MidCircuitMeasure(Instruction):
    """
    This instruction implements an alternative 'named' measurement definition
    (1 classical bit, 1 quantum bit), whose name can be used to map to a corresponding
    mid-circuit measurement instruction implementation on hardware.
    """

    def __init__(self, name: str = "measure_2", label: str = None) -> None:
        if not name.startswith("measure_"):
            raise ValueError(
                "Invalid name for mid-circuit measure instruction."
                "The provided name must start with `measure_`"
            )

        super().__init__(name, 1, 1, [], label=label)
