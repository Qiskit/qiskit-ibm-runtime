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

"""Primitive abstract base class."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, replace
from collections.abc import Sequence

from qiskit.circuit import QuantumCircuit


@dataclass
class BasePrimitiveOptions:

    def __call__(self):
        return replace(self)


class BasePrimitiveV2(ABC):
    """Version 2 of primitive abstract base class."""

    version = 2

    def __init__(self, options: dict | None | BasePrimitiveOptions = None):

        pass

    @abstractmethod
    def set_options(self, **fields):
        """Set options values for the estimator.

        Args:
            **fields: The fields to update the options
        """
        raise NotImplementedError()


    @staticmethod
    def _validate_circuits(
        circuits: Sequence[QuantumCircuit] | QuantumCircuit,
    ) -> tuple[QuantumCircuit, ...]:
        if isinstance(circuits, QuantumCircuit):
            circuits = (circuits,)
        elif not isinstance(circuits, Sequence) or not all(
            isinstance(cir, QuantumCircuit) for cir in circuits
        ):
            raise TypeError("Invalid circuits, expected Sequence[QuantumCircuit].")
        elif not isinstance(circuits, tuple):
            circuits = tuple(circuits)
        if len(circuits) == 0:
            raise ValueError("No circuits were provided.")
        return circuits
