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

from typing import List, Tuple
from .falcon_info import edges as falcon_edges, coordinates as falcon_coordinates


class BackendVisualInfo:
    def __init__(
        self, edges: List[Tuple[int, int]], coordinates: Tuple[List[int], List[int]], cpu_type: str
    ) -> None:
        self._edges = edges
        self._coordinates = coordinates
        self._cpu_type: cpu_type

        # TODO: add validation

    @property
    def coordinates(self):
        return self._coordinates

    @property
    def cpu_type(self):
        return self._cpu_type

    @property
    def edges(self):
        return self._edges


FalconVisualInfo = BackendVisualInfo(falcon_edges, falcon_coordinates, "Falcon")
