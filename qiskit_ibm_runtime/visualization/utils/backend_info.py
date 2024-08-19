# This code is part of Qiskit.
#
# (C) Copyright IBM 2024.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Functions to visualize :class:`~.NoiseLearnerResult` objects."""

from __future__ import annotations

from typing import Iterable, List, Tuple
from .falcon_info import edges as falcon_edges, coordinates as falcon_coordinates


class BackendVisualInfo:
    r"""
    The information required to visualize the map view of a backend.

    Args:
        x_coo: The list of ``x`` coordinates for the qubits in this backend.
        y_coo: The list of ``y`` coordinates for the qubits in this backend.
        edges: The edges between connected qubits.
    """

    def __init__(self, x_coo: List[int], y_coo: List[int], edges: List[Tuple[int, int]]) -> None:
        # Validation
        if len(x_coo) != len(y_coo):
            raise ValueError("``x_coo`` and ``y_coo`` must be of the same length.")

        self._x_coo = x_coo
        self._y_coo = y_coo
        self._edges = edges

    @property
    def coordinates(self) -> Iterable[List[int], List[int]]:
        """
        An iterable over ``x`` and ``y`` coordinates.
        """
        return zip(self.x_coo, self.y_coo)

    @property
    def x_coo(self) -> List[int]:
        """
        The ``x`` coordinates of the qubits in this backend.
        """
        return self._x_coo

    @property
    def y_coo(self) -> List[int]:
        """
        The ``y`` coordinates of the qubits in this backend.
        """
        return self._y_coo

    @property
    def edges(self) -> List[Tuple[int, int]]:
        """
        The edges representing the qubit-qubit connections in this backend.
        """
        return self._edges


r"""The visual information required to visualize a Falcon QPU."""
FalconVisualInfo = BackendVisualInfo(falcon_edges, falcon_coordinates, "Falcon")
