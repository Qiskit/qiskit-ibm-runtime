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

from qiskit.circuit import QuantumCircuit
from qiskit.quantum_info import PauliList
from qiskit.primitives import EstimatorResult


@dataclass(frozen=True)
class NoiseLearnerDatum:
    """A container for a single noise learner datum.

    Args:
        circuit: A circuit whose noise has been learnt.
        qubits: The labels of the qubits in the given circuit.
        generators: The list of generators for the Pauli errors.
        rates: The rates for the given Pauli error generators.

    Raises:
        ValueError: If ``circuit``, ``qubits``, and ``generators`` have mismatching number of
            qubits.
        ValueError: If ``generators`` and ``rates`` have different lengths.
    """

    circuit: QuantumCircuit
    qubits: Iterable[int]
    generators: PauliList
    rates: Iterable[float]

    def __post_init__(self):
        if len({self.circuit.num_qubits, len(self.qubits), self.generators.num_qubits}) != 1:
            raise ValueError("Mistmatching numbers of qubits.")
        if len(self.generators) != len(self.rates):
            msg = f"``generators`` has length {len(self.generators)}, but "
            msg += f"``rates`` has length {len(self.rates)}."
            raise ValueError(msg)


class NoiseLearnerResult:
    """A container for the results of a noise learner experiment."""

    def __init__(self, data: Iterable[NoiseLearnerDatum], metadata: dict[str, Any] | None = None):
        """
        Args:
            data: The data of a noise learner experiment.
            metadata: Metadata that is common to all pub results; metadata specific to particular
                pubs should be placed in their metadata fields. Keys are expected to be strings.
        """
        self._data = data
        self._metadata = metadata or {}

    @classmethod
    def from_estimator_result(cls, result: EstimatorResult) -> NoiseLearnerResult:
        """Construct noise learner results from estimator results.

        Args:
            result: The estimator results.
        """
        resilience = result.metadata["resilience"]
        try:
            noise_model = resilience["layer_noise_model"]
        except KeyError:
            return NoiseLearnerResult(data=[])

        data = []
        for layer in noise_model:
            datum = NoiseLearnerDatum(
                layer[0]["circuit"], layer[0]["qubits"], layer[1]["generators"], layer[1]["rates"]
            )
            data.append(datum)
        return NoiseLearnerResult(data)

    @property
    def data(self) -> dict[str, Any]:
        """The data of this noise learner result."""
        return self._data

    @property
    def metadata(self) -> dict[str, Any]:
        """The metadata of this noise learner result."""
        return self._metadata

    def __getitem__(self, index) -> NoiseLearnerDatum:
        return self.data[index]

    def __len__(self) -> int:
        return len(self.data)

    def __repr__(self) -> str:
        return f"NoiseLearnerResult(data={self.data}, metadata={self.metadata})"

    def __iter__(self) -> Iterable[NoiseLearnerDatum]:
        return iter(self.data)
