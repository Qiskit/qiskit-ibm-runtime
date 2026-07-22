# This code is part of Qiskit.
#
# (C) Copyright IBM 2026.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Transpiler pass that inserts Pauli-Lindblad noise after labeled barriers."""

from __future__ import annotations

import re
import warnings
from functools import partial
from typing import TYPE_CHECKING

from qiskit.circuit import QuantumCircuit
from qiskit.converters import circuit_to_dag
from qiskit.transpiler import TransformationPass

if TYPE_CHECKING:
    from collections.abc import Callable

    from qiskit.circuit import Qubit
    from qiskit.dagcircuit import DAGCircuit, DAGOpNode
    from qiskit.quantum_info import PauliLindbladMap

from qiskit.utils.optionals import HAS_AER
from qiskit_aer.noise import PauliLindbladError


def _find_qubit(dag: DAGCircuit, qubit: Qubit) -> int:
    return dag.find_bit(qubit).index


class InsertNoisePass(TransformationPass):
    """Transpiler pass that inserts Pauli-Lindblad noise channels after (or before) tagged barriers.

    Barriers whose labels match the pattern ``<pos><idx>@tag=<tag>`` are replaced with a
    sub-circuit consisting of the original barrier followed (or preceded) by a
    :class:`~qiskit_aer.noise.PauliLindbladError` looked up from ``noise_dict`` by ``<tag>``.

    Args:
        noise_dict: Map from gate-name tags to Pauli-Lindblad noise maps.  Pass ``None`` to
            perform a no-op (no noise is inserted).
        noise_after: If ``True`` (default), insert noise after the barrier; otherwise before.
        noise_scale: Multiplicative scale factor applied to all noise rates.
        warn_absent: If ``True`` (default), emit a warning when a tagged barrier's tag is not
            found in ``noise_dict``.  Set to ``False`` to suppress these warnings.
    """

    def __init__(
        self,
        noise_dict: dict[str, PauliLindbladMap] | None,
        noise_after: bool = True,
        noise_scale: float = 1.0,
        warn_absent: bool = True,
    ):
        if not HAS_AER:
            raise ValueError(
                "Cannot import this file since 'qiskit-aer' is not installed. Install 'qiskit-aer' "
                "and try again."
            )

        self._noise_dict = noise_dict or {}
        self._noise_after = noise_after
        self._noise_scale = noise_scale
        self._warn_absent = warn_absent

        self._pattern = re.compile(r"^(?P<pos>[A-Za-z])(?P<idx>\d+)(.*?)tag=(?P<tag>.+)(.*?)")

        super().__init__()

    def run(self, dag: DAGCircuit) -> DAGCircuit:
        """Run the pass."""
        if not self._noise_dict:
            return dag

        for op_node in reversed(list(dag.topological_op_nodes())):
            if op_node.name != "barrier":
                continue

            if _new_subdag := self._new_subdag(op_node, partial(_find_qubit, dag)):
                dag.substitute_node_with_dag(
                    node=op_node,
                    input_dag=_new_subdag,
                )

        return dag

    def _match_key(self, name: str) -> str | None:
        if not (match_group := self._pattern.match(name)):
            return None
        pos = match_group.group("pos")
        tag = match_group.group("tag")

        if self._noise_after:
            if pos != "R":
                return None
        else:
            if pos != "M":
                return None

        return tag

    def _new_subdag(
        self, op_node: DAGOpNode, find_qubit: Callable[[Qubit], int]
    ) -> DAGCircuit | None:
        # Qiskit has no public API for reading barrier labels; _label is the only option.
        label = op_node.op._label
        if label is None:
            return None
        if (noise_key := self._match_key(label)) is None:
            return None

        pauli_lindblad_map = self._noise_dict.get(noise_key)
        if pauli_lindblad_map is None:
            if self._noise_dict and self._warn_absent:
                warnings.warn(
                    f"No noise found for tag '{noise_key}'; "
                    f"available tags: {list(self._noise_dict.keys())}",
                    stacklevel=2,
                )
            return None

        if len(pauli_lindblad_map) == 0:
            return None

        pauli_lindblad_error = PauliLindbladError(
            generators=pauli_lindblad_map.generators().to_pauli_list(),
            rates=self._noise_scale * pauli_lindblad_map.rates,
        )

        # The PauliLindbladMap's indices are interpreted in ascending physical-qubit order
        # of the parent DAG, so we apply the resulting error to the local qc.qubits in the
        # permutation that orders op_node.qargs by their physical index.
        physical_indices = [find_qubit(q) for q in op_node.qargs]
        plm_indices = sorted(range(len(physical_indices)), key=physical_indices.__getitem__)

        qc = QuantumCircuit(op_node.num_qubits)
        qc.append(op_node.op, qc.qubits)
        qc.append(pauli_lindblad_error, [qc.qubits[i] for i in plm_indices])
        return circuit_to_dag(qc)
