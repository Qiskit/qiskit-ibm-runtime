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

from dataclasses import dataclass
from typing import List, Tuple, Union, Sequence

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
        try:
            coordinates = _get_qubits_coordinates(backend.num_qubits)
        except ValueError as err:
            raise ValueError(
                f"Failed to fetch coordinates for backend '{backend.name}' with error: {err}"
            )

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


@dataclass(frozen=True)
class _Row:
    r"""
    A class representing a dense row of the standard heavy hex planar embedding.

    Args:
        num_qubits: The number of qubits in the dense row.
        x_offset: The integer x-offset of the row.
        down_links: The positions of dense row, wrt the first qubit, at which to place qubits below.
    """

    num_qubits: int
    x_offset: int = 0
    down_links: Sequence[int] = ()


def _heavy_hex_coords(rows: Sequence[_Row], row_major: bool = True) -> List[Tuple[int, int]]:
    """Generate heavy hex coordinates for the given rows.

    Args:
        rows: The dense rows specifications.
        row_major: Whether qubits should be labelled in row-major order (by ``x`` first and, in
            case of a tie, by ``y``) or in colum-major order.

    Returns:
        A list of qubit coordinates, where list position corresponds with qubit index.
    """
    coordinates = []

    # Add coordinates in row-major order
    row_idx = 0
    for row in rows:
        if row.num_qubits:
            for col_idx in range(row.num_qubits):
                coordinates += [(row_idx, col_idx + row.x_offset)]
            row_idx += 1
        if row.down_links:
            for col_idx in row.down_links:
                coordinates += [(row_idx, col_idx + row.x_offset)]
            row_idx += 1

    # Sort if colum-major order is required
    if not row_major:
        coordinates = sorted(coordinates, key=lambda p: (p[1], p[0]))

    return coordinates


def _get_qubits_coordinates(num_qubits: int) -> List[Tuple[int, int]]:
    r"""
    Return a list of coordinates for drawing a set of qubits on a two-dimensional plane.

    The coordinates are in the form ``(row, column)``.

    If the coordinates are unknown, it returns an empty list.

    Args:
        num_qubits: The number of qubits to return the coordinates from.

    Returns:
        A list of coordinates for drawing a set of qubits on a two-dimensional plane.

    Raises:
        ValueError: If the coordinates for a backend with ``num_qubit`` qubits are unknown.
    """
    if num_qubits == 5:
        return [(1, 0), (0, 1), (1, 1), (1, 2), (2, 1)]

    if num_qubits == 7:
        rows = [_Row(3, 0, (1,)), _Row(3, 0)]
        return _heavy_hex_coords(rows)

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

    if num_qubits == 16:
        rows = [_Row(0, 0, (3,)), _Row(7, 0, (1, 5)), _Row(5, 1, (2,))]
        return _heavy_hex_coords(rows, False)

    if num_qubits == 20:
        rows = [row := _Row(5, 0), row, row, row]
        return _heavy_hex_coords(rows)

    if num_qubits == 27:
        rows = [_Row(0, 0, [3, 7]), _Row(10, 0, [1, 5, 9]), _Row(10, 1, [2, 6])]
        return _heavy_hex_coords(rows, False)

    if num_qubits == 28:
        rows = [
            _Row(5, 2, (0, 4)),
            _Row(9, 0, (0, 4, 8)),
            _Row(9, 0),
        ]
        return _heavy_hex_coords(rows=rows)

    if num_qubits == 53:
        rows = [
            _Row(5, 2, (0, 4)),
            r1 := _Row(9, 0, (0, 4, 8)),
            r2 := _Row(9, 0, (2, 6)),
            r1,
            r2,
        ]
        return _heavy_hex_coords(rows, True)

    if num_qubits == 65:
        rows = [
            _Row(10, 0, (0, 4, 8)),
            r := _Row(11, 0, (2, 6, 10)),
            _Row(11, 0, (0, 4, 8)),
            r,
            _Row(10, 1),
        ]
        return _heavy_hex_coords(rows, True)

    if num_qubits == 127:
        r1 = _Row(15, 0, (2, 6, 10, 14))
        r2 = _Row(15, 0, (0, 4, 8, 12))
        rows = [_Row(14, 0, (0, 4, 8, 12)), r1, r2, r1, r2, r1, _Row(14, 1)]
        return _heavy_hex_coords(rows, True)

    raise ValueError(f"Coordinates for {num_qubits}-qubit CPU are unknown.")
