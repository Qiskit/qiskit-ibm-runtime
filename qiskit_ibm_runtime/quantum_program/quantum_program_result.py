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

"""QuantumProgramResult"""

from __future__ import annotations

from typing import Union

import numpy as np


MetadataLeafTypes = Union[int, str, float]
MetadataValue = Union[MetadataLeafTypes, "Metadata", list["MetadataValue"]]
Metadata = dict[str, MetadataValue]


class QuantumProgramResult:
    """A container to store results from executing a :class:`QuantumProgram`.

    Args:
        data: A list of dictionaries with array-valued data.
        metadata: A dictionary of metadata.
    """

    def __init__(self, data: list[dict[str, np.ndarray]], metadata: Metadata | None = None):
        self._data = data
        self.metadata = metadata or {}

    def __iter__(self):
        yield from self._data

    def __getitem__(self, idx):
        return self._data[idx]

    def __len__(self):
        return len(self._data)

    def __repr__(self):
        return f"{type(self).__name__}(<{len(self)} results>)"
