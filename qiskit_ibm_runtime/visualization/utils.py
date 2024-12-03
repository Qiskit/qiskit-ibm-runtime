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

from __future__ import annotations

import importlib
from types import ModuleType

import numpy as np


def plotly_module(submodule: str = ".") -> ModuleType:
    """Import and return a plotly module.

    Args:
        submodule: The plotly submodule to import, relative or absolute.

    Returns:
        The submodule.

    Raises:
        ModuleNotFoundError: If it can't be imported.
    """
    try:
        return importlib.import_module(submodule, "plotly")
    except (ModuleNotFoundError, ImportError) as ex:
        raise ModuleNotFoundError(
            "The plotly Python package is required for visualization. "
            "Install all qiskit-ibm-runtime visualization dependencies with "
            "pip install 'qiskit-ibm-runtime[visualization]'."
        ) from ex


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

    Returns:
        A path string.
    """
    t = np.linspace(angle_st * np.pi / 180, angle_end * np.pi / 180, 10)

    path_xs = x + radius * np.cos(t)
    path_ys = y + radius * np.sin(t)
    path = f"M {path_xs[0]},{path_ys[0]}"

    for xc, yc in zip(path_xs[1:], path_ys[1:]):
        path += f" L{xc},{yc}"
    path += f"L{x},{y} Z"

    return path


def get_rgb_color(
    discreet_colorscale: list[str], val: float, default: str, color_out_of_scale: str
) -> str:
    r"""
    Map a float to an RGB color based on a discreet colorscale that contains
    exactly ``1000`` hues.

    Args:
        discreet_colorscale: A discreet colorscale.
        val: A value to map to a color.
        default: A default color returned when ``val`` is ``0``.
        color_out_of_scale: The color that is returned when ``val`` is larger than ``1``.

    Raises:
        ValueError: If the colorscale contains more or less than ``1000`` hues.
    """
    if len(discreet_colorscale) != 1000:
        raise ValueError("Invalid ``discreet_colorscale.``")

    if val > 1:
        return color_out_of_scale
    if val == 1:
        return discreet_colorscale[-1]
    if val == 0:
        return default
    return discreet_colorscale[int(np.round(val, 3) * 1000)]
