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

from typing import Any, Iterator, List, Sequence
from numpy.typing import NDArray
import numpy as np

from qiskit.circuit import QuantumCircuit
from qiskit.quantum_info import PauliList


class PauliLindbladError:
    """
    A container for the generators and rates of an error channel in the sparse Pauli-Lindblad noise
    model.

    Args:
        generators: A list of the Pauli Lindblad generators for the error channel.
        rates: A list of the rates for the Pauli-Lindblad ``generators``.

    Raises:
        ValueError: If ``generators`` and ``rates`` have different lengths.
    """

    def __init__(self, generators: PauliList, rates: Sequence[float]) -> None:
        if len(generators) != len(rates):
            msg = f"``generators`` has length {len(generators)} "
            msg += f"but ``rates`` has length {len(rates)}."
            raise ValueError(msg)

        self._generators = generators
        self._rates = np.asarray(rates, dtype=float)

    @property
    def generators(self) -> PauliList:
        r"""
        The Pauli Lindblad generators of this :class:`~.PauliLindbladError`.
        """
        return self._generators

    @property
    def rates(self) -> NDArray[np.float64]:
        r"""
        The Lindblad generator rates of this quantum error.
        """
        return self._rates

    @property
    def num_qubits(self) -> int:
        r"""
        The number of qubits in this :class:`~.PauliLindbladError`.
        """
        return self.generators.num_qubits

    def __repr__(self) -> str:
        return f"PauliLindbladError(generators={self.generators}, rates={self.rates.tolist()})"


class LayerError:
    """The error channel (in Pauli-Lindblad format) of a single layer of instructions.

    Args:
        circuit: A circuit whose noise has been learnt.
        qubits: The labels of the qubits in the ``circuit``.
        error: The Pauli Lindblad error channel affecting the ``circuit``.

    Raises:
        ValueError: If ``circuit``, ``qubits``, and ``error`` have mismatching number of qubits.
    """

    def __init__(
        self, circuit: QuantumCircuit, qubits: Sequence[int], error: PauliLindbladError
    ) -> None:
        self._circuit = circuit
        self._qubits = list(qubits)
        self._error = error

        if len({self.circuit.num_qubits, len(self.qubits), self.error.num_qubits}) != 1:
            raise ValueError("Mistmatching numbers of qubits.")

    @property
    def circuit(self) -> QuantumCircuit:
        r"""
        The circuit in this :class:`.~LayerError`.
        """
        return self._circuit

    @property
    def qubits(self) -> List[int]:
        r"""
        The qubits in this :class:`.~LayerError`.
        """
        return self._qubits

    @property
    def error(self) -> PauliLindbladError:
        r"""
        The error channel in this :class:`.~LayerError`.
        """
        return self._error

    @property
    def num_qubits(self) -> int:
        r"""
        The number of qubits in this :class:`~.LayerError`.
        """
        return len(self.qubits)

    def __repr__(self) -> str:
        ret = f"circuit={repr(self.circuit)}, qubits={self.qubits}, error={self.error})"
        return f"LayerError({ret})"


class NoiseLearnerResult:
    """A container for the results of a noise learner experiment."""

    def __init__(self, data: Sequence[LayerError], metadata: dict[str, Any] | None = None):
        """
        Args:
            data: The data of a noise learner experiment.
            metadata: Metadata that is common to all pub results; metadata specific to particular
                pubs should be placed in their metadata fields. Keys are expected to be strings.
        """
        self._data = list(data)
        self._metadata = metadata.copy() or {}

    @property
    def data(self) -> List[LayerError]:
        """The data of this noise learner result."""
        return self._data

    @property
    def metadata(self) -> dict[str, Any]:
        """The metadata of this noise learner result."""
        return self._metadata

    def __getitem__(self, index: int) -> LayerError:
        return self.data[index]

    def __len__(self) -> int:
        return len(self.data)

    def __repr__(self) -> str:
        return f"NoiseLearnerResult(data={self.data}, metadata={self.metadata})"

    def __iter__(self) -> Iterator[LayerError]:
        return iter(self.data)
