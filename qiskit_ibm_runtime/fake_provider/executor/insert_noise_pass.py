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

"""Transpiler pass that inserts Pauli-Lindblad noise at labeled barriers."""

from __future__ import annotations

import re
from functools import partial
from typing import TYPE_CHECKING, NamedTuple

from qiskit.circuit import QuantumCircuit
from qiskit.converters import circuit_to_dag
from qiskit.transpiler import TransformationPass
from qiskit.utils.optionals import HAS_AER

if TYPE_CHECKING:
    from collections.abc import Callable

    from qiskit.circuit import Qubit
    from qiskit.dagcircuit import DAGCircuit, DAGOpNode
    from qiskit.quantum_info import PauliLindbladMap

if HAS_AER:
    from qiskit_aer.noise import PauliLindbladError

POSITIONS = ("L", "M", "R")
"""The barrier position letters samplomatic emits around each dressed box."""

# ``<pos><idx>[@<key>=<value>&...]``.  The index is a scope index, which contains an underscore for
# each level of box nesting (``0``, ``0_0``, ``1_2_3``); it is matched but not used.
_LABEL_PATTERN = re.compile(r"^(?P<pos>[A-Za-z])\d+(?:_\d+)*(?:@(?P<params>.*))?$")


class _BarrierLabel(NamedTuple):
    """The parsed contents of a samplomatic box barrier label."""

    position: str
    """The position letter, one of :data:`POSITIONS`."""

    params: dict[str, str]
    """The ``key=value`` pairs carried by the label."""


def _parse_barrier_label(label: str) -> _BarrierLabel | None:
    """Parse a samplomatic box barrier label.

    Args:
        label: The barrier label to parse.

    Returns:
        The parsed label, or ``None`` if ``label`` is not a samplomatic box barrier label.
    """
    if not (match := _LABEL_PATTERN.match(label)):
        return None

    params = {}
    for field in (match["params"] or "").split("&"):
        key, separator, value = field.partition("=")
        if separator:
            params[key] = value

    return _BarrierLabel(match["pos"], params)


def barrier_tags(circuit: QuantumCircuit) -> set[str]:
    """Return the layer tags carried by a circuit's box barriers.

    Args:
        circuit: A flattened template circuit.
    """
    tags = set()
    for instruction in circuit.data:
        # Qiskit has no public API for reading barrier labels; _label is the only option.
        if instruction.operation.name != "barrier" or not (label := instruction.operation._label):  # noqa: SLF001
            continue
        if (parsed := _parse_barrier_label(label)) and (tag := parsed.params.get("tag")):
            tags.add(tag)
    return tags


def pauli_lindblad_error(
    pauli_lindblad_map: PauliLindbladMap, noise_scale: float = 1.0
) -> PauliLindbladError:
    """Build the Aer error implementing a Pauli-Lindblad map, with its rates scaled.

    Args:
        pauli_lindblad_map: The map to realise.
        noise_scale: Multiplicative scale factor applied to the rates.
    """
    return PauliLindbladError(
        generators=pauli_lindblad_map.get_qubit_sparse_pauli_list_copy().to_pauli_list(),
        rates=noise_scale * pauli_lindblad_map.rates,
    )


def _find_qubit(dag: DAGCircuit, qubit: Qubit) -> int:
    return dag.find_bit(qubit).index


@HAS_AER.require_in_instance
class InsertNoisePass(TransformationPass):
    """Insert Pauli-Lindblad noise channels immediately after tagged barriers.

    Barriers are labeled ``<pos><idx>[@<key>=<value>&...]`` (e.g. ``R0@tag=r0``). A
    :class:`~qiskit_aer.noise.PauliLindbladError` is inserted immediately after a barrier whose
    ``tag`` and position letter both appear in ``noise_dict``.

    .. code-block:: python

        noise_dict = {"layer": {"R": layer_map}, "spam": {"M": readout_map, "R": reset_map}}

    Args:
        noise_dict: Map from barrier tag to a map from position (one of :data:`POSITIONS`) to the
            noise inserted there, or ``None`` (or empty) to leave the circuit unchanged.  Each
            noise map must be defined on the qubits its barrier applies to, indexed in ascending
            circuit order: for a barrier on qubits ``(2, 0)`` of a three-qubit circuit, index 0 of
            a two-qubit map is qubit 0 and index 1 is qubit 2, so ``("IX", 0.1)`` places noise on
            qubit 0 and ``("XI", 0.1)`` places it on qubit 2.
        noise_scale: Multiplicative scale factor applied to all noise rates.

    Raises:
        ValueError: If ``noise_dict`` contains a position that is not one of :data:`POSITIONS`.
    """

    def __init__(
        self,
        noise_dict: dict[str, dict[str, PauliLindbladMap]] | None,
        noise_scale: float = 1.0,
    ):
        self._noise_dict = noise_dict or {}
        self._noise_scale = noise_scale

        for tag, by_position in self._noise_dict.items():
            if invalid := sorted(set(by_position) - set(POSITIONS)):
                raise ValueError(
                    f"Noise for tag '{tag}' uses unknown barrier position(s) {invalid}; "
                    f"expected one of {list(POSITIONS)}."
                )

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

    def _lookup(self, label: str) -> PauliLindbladMap | None:
        """Return the noise to insert at the barrier with this label, if any."""
        if (parsed := _parse_barrier_label(label)) is None:
            return None
        if parsed.position not in POSITIONS:
            return None
        if (tag := parsed.params.get("tag")) is None:
            return None

        return self._noise_dict.get(tag, {}).get(parsed.position)

    def _new_subdag(
        self, op_node: DAGOpNode, find_qubit: Callable[[Qubit], int]
    ) -> DAGCircuit | None:
        # Qiskit has no public API for reading barrier labels; _label is the only option.
        label = op_node.op._label
        if label is None:
            return None

        pauli_lindblad_map = self._lookup(label)
        if pauli_lindblad_map is None:
            return None

        if len(pauli_lindblad_map) == 0:
            return None

        # The PauliLindbladMap's indices are interpreted in ascending physical-qubit order
        # of the parent DAG, so we apply the resulting error to the local qc.qubits in the
        # permutation that orders op_node.qargs by their physical index.
        physical_indices = [find_qubit(q) for q in op_node.qargs]
        plm_indices = sorted(range(len(physical_indices)), key=physical_indices.__getitem__)

        qc = QuantumCircuit(op_node.num_qubits)
        qc.append(op_node.op, qc.qubits)
        qc.append(
            pauli_lindblad_error(pauli_lindblad_map, self._noise_scale),
            [qc.qubits[i] for i in plm_indices],
        )
        return circuit_to_dag(qc)
