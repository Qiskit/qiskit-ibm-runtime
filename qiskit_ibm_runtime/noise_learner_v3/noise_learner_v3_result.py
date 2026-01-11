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

"""Noise learner V3 results."""

from __future__ import annotations

from typing import Union
from collections.abc import Iterable, Sequence
from numpy.typing import NDArray

import numpy as np
from qiskit.circuit import BoxOp, CircuitInstruction
from qiskit.quantum_info import PauliLindbladMap, QubitSparsePauliList

from samplomatic import InjectNoise
from samplomatic.utils import get_annotation

MetadataLeafTypes = int | str | float
MetadataValue = Union[MetadataLeafTypes, "Metadata", list["MetadataValue"]]
Metadata = dict[str, MetadataValue]


class NoiseLearnerV3Result:
    r"""The results of a noise learner experiment for a single instruction, in Pauli Lindblad format.

    An error channel Pauli Lindblad :math:`E` acting on a state :math:`\rho` can be expressed in Pauli
    Lindblad format as :math:`E(\rho) = e^{\sum_j r_j D_{P_j}}(\rho)`, :math:`P_j` are Pauli operators
    (or "generators") and :math:`r_j` are floats (or "rates") [1]. The equivalent Pauli error channel
    can be constructed as a composition of single-Pauli channel terms

    .. math::

        E = e^{\sum_j r_j D_{P_j}} = \prod_j e^{r_j D_{P_j}}
        = prod_j \left( (1 - p_j) S_I + p_j S_{P_j} \right)

    where :math:`p_j = \frac12 - \frac12 e^{-2 r_j}`.

    Some strategies for learning noise channels, such as the Pauli Lindblad learning protocol in
    Ref. [1], produce degenerate terms, meaning that they learn products of rates as opposed to
    individual rates.

    References:
        1. E. van den Berg, Z. Minev, A. Kandala, K. Temme, *Probabilistic error
           cancellation with sparse Pauli–Lindblad models on noisy quantum processors*,
           Nature Physics volume 19, pages 1116–1121 (2023).
           `arXiv:2201.09866 [quant-ph] <https://arxiv.org/abs/2201.09866>`_
    """

    def __init__(self) -> None:
        self._generators: list[QubitSparsePauliList] = []
        self._rates: NDArray[np.float64] = np.array([])
        self._rates_std: NDArray[np.float64] = np.array([])
        self.metadata: MetadataValue = {}

    @classmethod
    def from_generators(
        cls,
        generators: Iterable[QubitSparsePauliList],
        rates: Iterable[float],
        rates_std: Iterable[float] | None = None,
        metadata: Metadata | None = None,
    ) -> NoiseLearnerV3Result:
        """
        Construct from a collection of generators and rates.

        Args:
            generators: The generators describing the noise channel in the Pauli Lindblad format. This
                is a list of :class:`~qiskit.quantum_info.QubitSparsePauliList` objects, as opposed to
                a list of :class:`~qiskit.quantum_info.QubitSparsePauli`, in order to capture
                degeneracies present within the model.
            rates: The rates of the individual generators. The ``i``-th element in this list represents
                the rate of all the Paulis in the ``i``-th generator.
            rates_std: The standard deviation associated to the rates of the generators. If ``None``,
                it sets all the standard deviations to ``0``.
            metadata: A dictionary of metadata.
        """
        obj = cls()
        obj._generators = list(generators)
        obj._rates = np.array(rates, dtype=np.float64)
        obj._rates_std = np.array(
            [0] * len(obj._generators) if rates_std is None else rates_std, dtype=np.float64
        )
        obj.metadata = metadata or {}

        if len({len(obj._generators), len(obj._rates), len(obj._rates_std)}) != 1:
            raise ValueError("'generators', 'rates', and 'rates_std' must be of the same length.")

        if len({generator.num_qubits for generator in obj._generators}) != 1:
            raise ValueError("All the generators must have the same number of qubits.")

        return obj

    def to_pauli_lindblad_map(self) -> PauliLindbladMap:
        """Transform this result to a Pauli Lindblad map.

        The Pauli terms in the generators are indexed in physical qubit order, that is, the order
        of the qubits in the outer-most circuit.
        """
        coefficients = [
            repeated_rate
            for generator, rate in zip(self._generators, self._rates)
            for repeated_rate in [rate] * len(generator)
        ]
        paulis = QubitSparsePauliList.from_qubit_sparse_paulis(
            pauli for generator in self._generators for pauli in generator
        )

        return PauliLindbladMap.from_components(coefficients, paulis)

    def __len__(self) -> int:
        return len(self._generators)

    def __repr__(self) -> str:
        return f"NoiseLearnerV3Result(<{len(self)}> generators)"


class NoiseLearnerV3Results:
    """The results of a noise learner experiment.

    Args:
        data: The data in this result object.
        metadata: A dictionary of metadata.
    """

    def __init__(self, data: Iterable[NoiseLearnerV3Result], metadata: Metadata | None = None):
        self.data = list(data)
        self.metadata = metadata or None

    def to_dict(
        self,
        instructions: Sequence[CircuitInstruction],
        require_refs: bool = True,
    ) -> dict[int, PauliLindbladMap]:
        """Convert to a dictionary from :attr:`InjectNoise.ref` to :class:`PauliLindbladMap` objects.
        This function iterates over a sequence of instructions, extracts the ``ref`` value from the
        inject noise annotation of each instruction, and returns a dictionary mapping those refs
        to the corresponding noise data (in :class:`PauliLindbladMap` format) stored in this
        :class:`NoiseLearnerV3Results` object.

        Args:
            instructions: The instructions to get the refs from.
            require_refs: Whether to raise if some of the instructions do not own an inject noise
                annotation. If ``False``, all the instructions that do not contain an inject noise
                annotations are simply skipped when constructing the returned dictionary.

        Raise:
            ValueError: If ``instructions`` contains a number of elements that is not equal to the
                item in this :class:`NoiseLearnerV3Results` object.
            ValueError: If some of the instructions do not contain a box.
            ValueError: If multiple instructions have the same ``ref``.
            ValueError: If some of the instructions have no inject noise annotation and ``require_refs``
                if ``True``.
        """
        if len(instructions) != len(self.data):
            raise ValueError(
                f"Expected {len(self.data)} instructions but found {len(instructions)}."
            )

        noise_source = {}
        num_instr = 0
        for instr, datum in zip(instructions, self.data):
            if not isinstance(instr.operation, BoxOp):
                raise ValueError("Found an instruction that does not contain a box.")
            if annotation := get_annotation(instr.operation, InjectNoise):
                num_instr += 1
                noise_source[annotation.ref] = datum.to_pauli_lindblad_map()
            elif require_refs:
                raise ValueError(
                    "Found an instruction without an inject noise annotation. "
                    "Consider setting 'require_refs' to ``False``."
                )

        if num_instr != len(noise_source):
            raise ValueError("Found multiple instructions with the same ``ref``.")

        return noise_source

    def __getitem__(self, idx: int) -> NoiseLearnerV3Result:
        return self.data[idx]

    def __iter__(self) -> Iterable[NoiseLearnerV3Result]:
        return iter(self.data)

    def __len__(self) -> int:
        return len(self.data)

    def __repr__(self) -> str:
        return f"NoiseLearnerV3Results(<{len(self.data)}> data)"
