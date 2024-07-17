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

"""NoiseLearner result class"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class NoiseLearnerDatum:
    """A container for a single noise learner datum.

    Args:
        blocks: A dictionary that stores a circuit and the list of its qubits.
        errors: A dictionary that stores the error generators and the associated rates.

    Raises:
        # TODO
    """

    blocks: dict[Any, Any]
    errors: dict[Any, Any]

    def __post_init__(self):
        # TODO validation
        pass


class NoiseLearnerResult:
    """A container for the results of a noise learner experiment."""

    def __init__(self, data: Iterable[NoiseLearnerDatum], metadata: dict[str, Any] | None = None):
        """
        Args:
            data: The data of a noise learner experiment.
            metadata: Metadata that is common to all pub results; metadata specific to particular
                pubs should be placed in their metadata fields. Keys are expected to be strings.
        """
        self._data = [NoiseLearnerDatum(datum[0], datum[1]) for datum in data]
        self._metadata = metadata or {}

    @property
    def metadata(self) -> dict[str, Any]:
        """The metadata of this primitive result."""
        return self._metadata

    def __getitem__(self, index) -> NoiseLearnerDatum:
        return self._data[index]

    def __len__(self) -> int:
        return len(self._data)

    def __repr__(self) -> str:
        return f"NoiseLearnerResult(data={self._data}, metadata={self.metadata})"

    def __iter__(self) -> Iterable[NoiseLearnerDatum]:
        return iter(self._data)
