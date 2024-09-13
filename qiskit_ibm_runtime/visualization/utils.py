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
Utility functions for visualizing qiskit-ibm-runtime's objects.
"""

from typing import List
import numpy as np


def get_qubits_coordinates(num_qubits: int) -> List[List[int]]:
    r"""
    Return a list of coordinates for drawing a QPU map on a 2D grid.

    The coordinates are in the form ``(row, column)``.

    Args:
        num_qubits: The number of qubits to return the coordinates from.
    """
    if num_qubits == 5:
        return [[1, 0], [0, 1], [1, 1], [1, 2], [2, 1]]

    if num_qubits == 7:
        return [[0, 0], [0, 1], [0, 2], [1, 1], [2, 0], [2, 1], [2, 2]]

    if num_qubits == 20:
        return [
            [0, 0],
            [0, 1],
            [0, 2],
            [0, 3],
            [0, 4],
            [1, 0],
            [1, 1],
            [1, 2],
            [1, 3],
            [1, 4],
            [2, 0],
            [2, 1],
            [2, 2],
            [2, 3],
            [2, 4],
            [3, 0],
            [3, 1],
            [3, 2],
            [3, 3],
            [3, 4],
        ]

    if num_qubits == 15:
        return [
            [0, 0],
            [0, 1],
            [0, 2],
            [0, 3],
            [0, 4],
            [0, 5],
            [0, 6],
            [1, 7],
            [1, 6],
            [1, 5],
            [1, 4],
            [1, 3],
            [1, 2],
            [1, 1],
            [1, 0],
        ]

    if num_qubits == 16:
        return [
            [1, 0],
            [1, 1],
            [2, 1],
            [3, 1],
            [1, 2],
            [3, 2],
            [0, 3],
            [1, 3],
            [3, 3],
            [4, 3],
            [1, 4],
            [3, 4],
            [1, 5],
            [2, 5],
            [3, 5],
            [1, 6],
        ]

    if num_qubits == 27:
        return [
            [1, 0],
            [1, 1],
            [2, 1],
            [3, 1],
            [1, 2],
            [3, 2],
            [0, 3],
            [1, 3],
            [3, 3],
            [4, 3],
            [1, 4],
            [3, 4],
            [1, 5],
            [2, 5],
            [3, 5],
            [1, 6],
            [3, 6],
            [0, 7],
            [1, 7],
            [3, 7],
            [4, 7],
            [1, 8],
            [3, 8],
            [1, 9],
            [2, 9],
            [3, 9],
            [3, 10],
        ]

    if num_qubits == 28:
        return [
            [0, 2],
            [0, 3],
            [0, 4],
            [0, 5],
            [0, 6],
            [1, 2],
            [1, 6],
            [2, 0],
            [2, 1],
            [2, 2],
            [2, 3],
            [2, 4],
            [2, 5],
            [2, 6],
            [2, 7],
            [2, 8],
            [3, 0],
            [3, 4],
            [3, 8],
            [4, 0],
            [4, 1],
            [4, 2],
            [4, 3],
            [4, 4],
            [4, 5],
            [4, 6],
            [4, 7],
            [4, 8],
        ]

    if num_qubits == 53:
        return [
            [0, 2],
            [0, 3],
            [0, 4],
            [0, 5],
            [0, 6],
            [1, 2],
            [1, 6],
            [2, 0],
            [2, 1],
            [2, 2],
            [2, 3],
            [2, 4],
            [2, 5],
            [2, 6],
            [2, 7],
            [2, 8],
            [3, 0],
            [3, 4],
            [3, 8],
            [4, 0],
            [4, 1],
            [4, 2],
            [4, 3],
            [4, 4],
            [4, 5],
            [4, 6],
            [4, 7],
            [4, 8],
            [5, 2],
            [5, 6],
            [6, 0],
            [6, 1],
            [6, 2],
            [6, 3],
            [6, 4],
            [6, 5],
            [6, 6],
            [6, 7],
            [6, 8],
            [7, 0],
            [7, 4],
            [7, 8],
            [8, 0],
            [8, 1],
            [8, 2],
            [8, 3],
            [8, 4],
            [8, 5],
            [8, 6],
            [8, 7],
            [8, 8],
            [9, 2],
            [9, 6],
        ]

    if num_qubits == 65:
        return [
            [0, 0],
            [0, 1],
            [0, 2],
            [0, 3],
            [0, 4],
            [0, 5],
            [0, 6],
            [0, 7],
            [0, 8],
            [0, 9],
            [1, 0],
            [1, 4],
            [1, 8],
            [2, 0],
            [2, 1],
            [2, 2],
            [2, 3],
            [2, 4],
            [2, 5],
            [2, 6],
            [2, 7],
            [2, 8],
            [2, 9],
            [2, 10],
            [3, 2],
            [3, 6],
            [3, 10],
            [4, 0],
            [4, 1],
            [4, 2],
            [4, 3],
            [4, 4],
            [4, 5],
            [4, 6],
            [4, 7],
            [4, 8],
            [4, 9],
            [4, 10],
            [5, 0],
            [5, 4],
            [5, 8],
            [6, 0],
            [6, 1],
            [6, 2],
            [6, 3],
            [6, 4],
            [6, 5],
            [6, 6],
            [6, 7],
            [6, 8],
            [6, 9],
            [6, 10],
            [7, 2],
            [7, 6],
            [7, 10],
            [8, 1],
            [8, 2],
            [8, 3],
            [8, 4],
            [8, 5],
            [8, 6],
            [8, 7],
            [8, 8],
            [8, 9],
            [8, 10],
        ]

    if num_qubits == 127:
        return [
            [0, 0],
            [0, 1],
            [0, 2],
            [0, 3],
            [0, 4],
            [0, 5],
            [0, 6],
            [0, 7],
            [0, 8],
            [0, 9],
            [0, 10],
            [0, 11],
            [0, 12],
            [0, 13],
            [1, 0],
            [1, 4],
            [1, 8],
            [1, 12],
            [2, 0],
            [2, 1],
            [2, 2],
            [2, 3],
            [2, 4],
            [2, 5],
            [2, 6],
            [2, 7],
            [2, 8],
            [2, 9],
            [2, 10],
            [2, 11],
            [2, 12],
            [2, 13],
            [2, 14],
            [3, 2],
            [3, 6],
            [3, 10],
            [3, 14],
            [4, 0],
            [4, 1],
            [4, 2],
            [4, 3],
            [4, 4],
            [4, 5],
            [4, 6],
            [4, 7],
            [4, 8],
            [4, 9],
            [4, 10],
            [4, 11],
            [4, 12],
            [4, 13],
            [4, 14],
            [5, 0],
            [5, 4],
            [5, 8],
            [5, 12],
            [6, 0],
            [6, 1],
            [6, 2],
            [6, 3],
            [6, 4],
            [6, 5],
            [6, 6],
            [6, 7],
            [6, 8],
            [6, 9],
            [6, 10],
            [6, 11],
            [6, 12],
            [6, 13],
            [6, 14],
            [7, 2],
            [7, 6],
            [7, 10],
            [7, 14],
            [8, 0],
            [8, 1],
            [8, 2],
            [8, 3],
            [8, 4],
            [8, 5],
            [8, 6],
            [8, 7],
            [8, 8],
            [8, 9],
            [8, 10],
            [8, 11],
            [8, 12],
            [8, 13],
            [8, 14],
            [9, 0],
            [9, 4],
            [9, 8],
            [9, 12],
            [10, 0],
            [10, 1],
            [10, 2],
            [10, 3],
            [10, 4],
            [10, 5],
            [10, 6],
            [10, 7],
            [10, 8],
            [10, 9],
            [10, 10],
            [10, 11],
            [10, 12],
            [10, 13],
            [10, 14],
            [11, 2],
            [11, 6],
            [11, 10],
            [11, 14],
            [12, 1],
            [12, 2],
            [12, 3],
            [12, 4],
            [12, 5],
            [12, 6],
            [12, 7],
            [12, 8],
            [12, 9],
            [12, 10],
            [12, 11],
            [12, 12],
            [12, 13],
            [12, 14],
        ]

    raise ValueError(
        f"Unknown coordinates for ``{num_qubits}``-qubit devices. Input ``coordinates`` must be "
        "provided."
    )


def pie_slice(angle_st: float, angle_end: float, x: float, y: float, radius: float) -> str:
    r"""
    Return a path that can be used to draw a slice of a pie chart with plotly.

    Note: To draw pie charts we use paths and shapes, as they are easier to place in a specific
    location than `go.Pie` objects.

    Args:
        angle_st: The angle (in degrees) where the slice begins.
        angle_end: The angle (in degrees) where the slice ends.
        x: The `x` coordinate of the centre of the pie.
        y: The `y` coordinate of the centre of the pie.
        radius: the radius of the pie.
    """
    t = np.linspace(angle_st * np.pi / 180, angle_end * np.pi / 180, 10)

    path_xs = x + radius * np.cos(t)
    path_ys = y + radius * np.sin(t)
    path = f"M {path_xs[0]},{path_ys[0]}"

    for xc, yc in zip(path_xs[1:], path_ys[1:]):
        path += f" L{xc},{yc}"
    path += f"L{x},{y} Z"

    return path


def get_rgb_color(discreet_colorscale: list[str], val: float, default: str) -> str:
    r"""
    Maps a float to an RGB color based on a discreet colorscale that contains
    exactly ``1000`` hues.

    Args:
        discreet_colorscale: A discreet colorscale.
        val: A value to map to a color.
        default: A default color returned when ``val`` is ``0``.

    Raises:
        ValueError: If the colorscale contains more or less than ``1000`` hues.
    """
    if len(discreet_colorscale) != 1000:
        raise ValueError("Invalid ``discreet_colorscale.``")

    if val >= 1:
        return discreet_colorscale[-1]
    if val == 0:
        return default
    return discreet_colorscale[int(np.round(val, 3) * 1000)]
