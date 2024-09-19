# This code is part of Qiskit.
#
# (C) Copyright IBM 2024
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.
# pylint: disable=too-many-return-statements

"""
Utility class to represent an embedding of a set of qubits in a two-dimensional plane.
"""

from typing import List, Tuple, Union

from qiskit.providers.backend import BackendV2
from qiskit.transpiler import CouplingMap


class Embedding:
    r"""
    A class to represent an embedding or arrangement of a set of qubits in a two-dimensional plane.

    Args:
        coordinates: A list of coordinates in the form ``(row, column)`` that specify the qubits'
            location on the 2D plane.
        coupling_map: A coupling map specifying how the qubits in the embedding are connected.
    """

    def __init__(
        self,
        coordinates: List[Tuple[int, int]],
        coupling_map: Union[List[Tuple[int, int]], CouplingMap],
    ) -> None:
        num_qubits = len(coordinates)
        if any(q0 > num_qubits or q1 > num_qubits for (q0, q1) in coupling_map):
            raise ValueError("Invalid coupling map.")

        self._coordinates = coordinates
        self._coupling_map = (
            coupling_map if isinstance(coupling_map, CouplingMap) else CouplingMap(coupling_map)
        )

    @classmethod
    def from_backend(cls, backend: BackendV2) -> "Embedding":
        r"""Generates an :class:`~.Embedding` object from a backend.

        Args:
            backend: A backend to generate the :class:`~.Embedding` object from.

        Returns:
            The embedding for the given backend.

        Raises:
            ValueError: If the given backend has coupling map set to ``None``.
            ValueError: If the coordinates for the given backend are unknown.
        """
        if not (coupling_map := backend.coupling_map):
            raise ValueError(f"Coupling map for backend '{backend.name}' is unknown.")
        if not (coordinates := _get_qubits_coordinates(backend.num_qubits)):
            raise ValueError(f"Coordinates for backend '{backend.name}' are unknown.")

        return cls(coordinates, coupling_map)

    @property
    def coordinates(self) -> List[Tuple[int, int]]:
        r"""
        The coordinates in this embedding.
        """
        return self._coordinates

    @property
    def coupling_map(self) -> CouplingMap:
        r"""
        The coupling map in this embedding.
        """
        return self._coupling_map


def _get_qubits_coordinates(num_qubits: int) -> List[Tuple[int, int]]:
    r"""
    Return a list of coordinates for drawing a set of qubits on a two-dimensional plane.

    The coordinates are in the form ``(row, column)``.

    If the coordinates are unknown, it returns an empty list.

    Args:
        num_qubits: The number of qubits to return the coordinates from.
    """
    if num_qubits == 5:
        return [(1, 0), (0, 1), (1, 1), (1, 2), (2, 1)]

    if num_qubits == 7:
        return [(0, 0), (0, 1), (0, 2), (1, 1), (2, 0), (2, 1), (2, 2)]

    if num_qubits == 15:
        return [
            (0, 0),
            (0, 1),
            (0, 2),
            (0, 3),
            (0, 4),
            (0, 5),
            (0, 6),
            (1, 7),
            (1, 6),
            (1, 5),
            (1, 4),
            (1, 3),
            (1, 2),
            (1, 1),
            (1, 0),
        ]

    if num_qubits == 20:
        return [
            (0, 0),
            (0, 1),
            (0, 2),
            (0, 3),
            (0, 4),
            (1, 0),
            (1, 1),
            (1, 2),
            (1, 3),
            (1, 4),
            (2, 0),
            (2, 1),
            (2, 2),
            (2, 3),
            (2, 4),
            (3, 0),
            (3, 1),
            (3, 2),
            (3, 3),
            (3, 4),
        ]

    if num_qubits == 16:
        return [
            (1, 0),
            (1, 1),
            (2, 1),
            (3, 1),
            (1, 2),
            (3, 2),
            (0, 3),
            (1, 3),
            (3, 3),
            (4, 3),
            (1, 4),
            (3, 4),
            (1, 5),
            (2, 5),
            (3, 5),
            (1, 6),
        ]

    if num_qubits == 27:
        return [
            (1, 0),
            (1, 1),
            (2, 1),
            (3, 1),
            (1, 2),
            (3, 2),
            (0, 3),
            (1, 3),
            (3, 3),
            (4, 3),
            (1, 4),
            (3, 4),
            (1, 5),
            (2, 5),
            (3, 5),
            (1, 6),
            (3, 6),
            (0, 7),
            (1, 7),
            (3, 7),
            (4, 7),
            (1, 8),
            (3, 8),
            (1, 9),
            (2, 9),
            (3, 9),
            (3, 10),
        ]

    if num_qubits == 28:
        return [
            (0, 2),
            (0, 3),
            (0, 4),
            (0, 5),
            (0, 6),
            (1, 2),
            (1, 6),
            (2, 0),
            (2, 1),
            (2, 2),
            (2, 3),
            (2, 4),
            (2, 5),
            (2, 6),
            (2, 7),
            (2, 8),
            (3, 0),
            (3, 4),
            (3, 8),
            (4, 0),
            (4, 1),
            (4, 2),
            (4, 3),
            (4, 4),
            (4, 5),
            (4, 6),
            (4, 7),
            (4, 8),
        ]

    if num_qubits == 53:
        return [
            (0, 2),
            (0, 3),
            (0, 4),
            (0, 5),
            (0, 6),
            (1, 2),
            (1, 6),
            (2, 0),
            (2, 1),
            (2, 2),
            (2, 3),
            (2, 4),
            (2, 5),
            (2, 6),
            (2, 7),
            (2, 8),
            (3, 0),
            (3, 4),
            (3, 8),
            (4, 0),
            (4, 1),
            (4, 2),
            (4, 3),
            (4, 4),
            (4, 5),
            (4, 6),
            (4, 7),
            (4, 8),
            (5, 2),
            (5, 6),
            (6, 0),
            (6, 1),
            (6, 2),
            (6, 3),
            (6, 4),
            (6, 5),
            (6, 6),
            (6, 7),
            (6, 8),
            (7, 0),
            (7, 4),
            (7, 8),
            (8, 0),
            (8, 1),
            (8, 2),
            (8, 3),
            (8, 4),
            (8, 5),
            (8, 6),
            (8, 7),
            (8, 8),
            (9, 2),
            (9, 6),
        ]

    if num_qubits == 65:
        return [
            (0, 0),
            (0, 1),
            (0, 2),
            (0, 3),
            (0, 4),
            (0, 5),
            (0, 6),
            (0, 7),
            (0, 8),
            (0, 9),
            (1, 0),
            (1, 4),
            (1, 8),
            (2, 0),
            (2, 1),
            (2, 2),
            (2, 3),
            (2, 4),
            (2, 5),
            (2, 6),
            (2, 7),
            (2, 8),
            (2, 9),
            (2, 10),
            (3, 2),
            (3, 6),
            (3, 10),
            (4, 0),
            (4, 1),
            (4, 2),
            (4, 3),
            (4, 4),
            (4, 5),
            (4, 6),
            (4, 7),
            (4, 8),
            (4, 9),
            (4, 10),
            (5, 0),
            (5, 4),
            (5, 8),
            (6, 0),
            (6, 1),
            (6, 2),
            (6, 3),
            (6, 4),
            (6, 5),
            (6, 6),
            (6, 7),
            (6, 8),
            (6, 9),
            (6, 10),
            (7, 2),
            (7, 6),
            (7, 10),
            (8, 1),
            (8, 2),
            (8, 3),
            (8, 4),
            (8, 5),
            (8, 6),
            (8, 7),
            (8, 8),
            (8, 9),
            (8, 10),
        ]

    if num_qubits == 127:
        return [
            (0, 0),
            (0, 1),
            (0, 2),
            (0, 3),
            (0, 4),
            (0, 5),
            (0, 6),
            (0, 7),
            (0, 8),
            (0, 9),
            (0, 10),
            (0, 11),
            (0, 12),
            (0, 13),
            (1, 0),
            (1, 4),
            (1, 8),
            (1, 12),
            (2, 0),
            (2, 1),
            (2, 2),
            (2, 3),
            (2, 4),
            (2, 5),
            (2, 6),
            (2, 7),
            (2, 8),
            (2, 9),
            (2, 10),
            (2, 11),
            (2, 12),
            (2, 13),
            (2, 14),
            (3, 2),
            (3, 6),
            (3, 10),
            (3, 14),
            (4, 0),
            (4, 1),
            (4, 2),
            (4, 3),
            (4, 4),
            (4, 5),
            (4, 6),
            (4, 7),
            (4, 8),
            (4, 9),
            (4, 10),
            (4, 11),
            (4, 12),
            (4, 13),
            (4, 14),
            (5, 0),
            (5, 4),
            (5, 8),
            (5, 12),
            (6, 0),
            (6, 1),
            (6, 2),
            (6, 3),
            (6, 4),
            (6, 5),
            (6, 6),
            (6, 7),
            (6, 8),
            (6, 9),
            (6, 10),
            (6, 11),
            (6, 12),
            (6, 13),
            (6, 14),
            (7, 2),
            (7, 6),
            (7, 10),
            (7, 14),
            (8, 0),
            (8, 1),
            (8, 2),
            (8, 3),
            (8, 4),
            (8, 5),
            (8, 6),
            (8, 7),
            (8, 8),
            (8, 9),
            (8, 10),
            (8, 11),
            (8, 12),
            (8, 13),
            (8, 14),
            (9, 0),
            (9, 4),
            (9, 8),
            (9, 12),
            (10, 0),
            (10, 1),
            (10, 2),
            (10, 3),
            (10, 4),
            (10, 5),
            (10, 6),
            (10, 7),
            (10, 8),
            (10, 9),
            (10, 10),
            (10, 11),
            (10, 12),
            (10, 13),
            (10, 14),
            (11, 2),
            (11, 6),
            (11, 10),
            (11, 14),
            (12, 1),
            (12, 2),
            (12, 3),
            (12, 4),
            (12, 5),
            (12, 6),
            (12, 7),
            (12, 8),
            (12, 9),
            (12, 10),
            (12, 11),
            (12, 12),
            (12, 13),
            (12, 14),
        ]

    return []
