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

"""
Base Pub class
"""

from __future__ import annotations

from dataclasses import dataclass

from qiskit import QuantumCircuit


@dataclass(frozen=True)
class BasePub:
    """Base class for Pub"""

    circuit: QuantumCircuit

    def validate(self) -> None:
        """Validate the inputs.

        Raises:
            TypeError: If input values has an invalid type.
        """
        if not isinstance(self.circuit, QuantumCircuit):
            raise TypeError("circuit must be QuantumCircuit.")
