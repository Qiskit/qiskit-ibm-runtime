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

from collections.abc import Iterator
from dataclasses import dataclass, field
import datetime

import numpy as np


@dataclass
class ChunkPart:
    """A description of the contents of a single part of an execution chunk."""

    idx_item: int
    """The index of an item in a quantum program."""

    size: int
    """The number of elements from the quantum program item that were executed.

    For example, if a quantum program item has shape ``(10, 5)``, then it has a total of ``50``
    elements, so that if this ``size`` is ``10``, it constitutes 20% of the total work for the item.
    """


@dataclass
class ChunkSpan:
    """Timing information about a single chunk of execution.

    .. note::

        This span may include some amount of non-circuit time.
    """

    start: datetime.datetime
    """The start time of the execution chunk in UTC."""

    stop: datetime.datetime
    """The stop time of the execution chunk in UTC."""

    parts: list[ChunkPart]
    """A description of which parts of a quantum program are contained in this chunk."""


@dataclass
class Metadata:
    """Metadata about the execution of a quantum program run through the runtime executor."""

    chunk_timing: list[ChunkSpan] = field(default_factory=list)
    """Timing information about all executed chunks of a quantum program."""


class QuantumProgramResult:
    """A container to store results from executing a :class:`QuantumProgram`.

    Args:
        data: A list of dictionaries with array-valued data.
        metadata: A dictionary of metadata.
    """

    def __init__(self, data: list[dict[str, np.ndarray]], metadata: Metadata | None = None):
        self._data = data
        self.metadata = metadata or Metadata()

    def __iter__(self) -> Iterator[dict[str, np.ndarray]]:
        yield from self._data

    def __getitem__(self, idx: int) -> dict[str, np.ndarray]:
        return self._data[idx]

    def __len__(self) -> int:
        return len(self._data)

    def __repr__(self) -> str:
        return f"{type(self).__name__}(<{len(self)} results>)"
