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
from .falcon_info import edges as falcon_edges, xs as falcon_xs, ys as falcon_ys


class BackendVisualInfo:
    r"""
    The information required to visualize the map view of a backend.

    Args:
        xs: The list of ``x`` coordinates for the qubits in this backend.
        ys: The list of ``y`` coordinates for the qubits in this backend.
        edges: The edges between connected qubits.
    """

    def __init__(self, xs: List[int], ys: List[int], edges: List[Tuple[int, int]]) -> None:
        # Validation
        if len(xs) != len(ys):
            raise ValueError("``xs`` and ``ys`` must be of the same length.")

        self._xs = xs
        self._ys = ys
        self._edges = edges

    @property
    def coordinates(self) -> Iterable[List[int], List[int]]:
        """
        An iterable over ``x`` and ``y`` coordinates.
        """
        return zip(self.xs, self.ys)

    @property
    def xs(self) -> List[int]:
        """
        The ``x`` coordinates of the qubits in this backend.
        """
        return self._xs

    @property
    def ys(self) -> List[int]:
        """
        The ``y`` coordinates of the qubits in this backend.
        """
        return self._ys

    @property
    def edges(self) -> List[Tuple[int, int]]:
        """
        The edges representing the qubit-qubit connections in this backend.
        """
        return self._edges


r"""The visual information required to visualize a Falcon QPU."""
FalconVisualInfo = BackendVisualInfo(falcon_xs, falcon_ys, falcon_edges)
