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

"""Scale noise factor of gates by gate folding."""

from __future__ import annotations

from typing import Literal

import numpy as np
from qiskit.circuit import Gate, QuantumCircuit
from qiskit.circuit.library import CXGate, CYGate, CZGate, ECRGate, SwapGate
from qiskit.converters import circuit_to_dag, dag_to_circuit
from qiskit.dagcircuit import DAGCircuit


DEFAULT_FOLDED_GATES: tuple[type, ...] = (ECRGate, CXGate, CYGate, CZGate, SwapGate)
"""Default 2-qubit gate types to fold."""


def fold_gates(
    circuit: QuantumCircuit,
    noise_factor: float,
    method: Literal["random", "front", "back"] = "random",
    seed: int | np.random.BitGenerator | None = None,
) -> QuantumCircuit:
    r"""Fold 2-qubit gates in ``circuit`` to amplify their noise by ``noise_factor``.

    Each foldable gate :math:`U` is replaced by :math:`U(U^\dagger U)^n` where
    :math:`n = (F - 1) / 2` for noise factor :math:`F \geq 1`. When ``noise_factor``
    is not such that every gate folds the same number of times, a subset of gates
    is folded one extra time; ``method`` controls which subset.

    Args:
        circuit: The circuit to fold.
        noise_factor: Target noise factor (``>= 1``).
        method: How to select the probabilistically-folded subset.
            ``"random"`` picks uniformly; ``"front"``/``"back"`` take the first/last
            gates in topological order.
        seed: Seed or BitGenerator for the random subset selection.

    Returns:
        The folded circuit.

    Raises:
        ValueError: If ``noise_factor`` is less than 1.
    """
    if noise_factor < 1:
        raise ValueError(f"noise_factor must be >= 1, got {noise_factor}.")
    if np.isclose(noise_factor, 1):
        return circuit.copy()

    dag = circuit_to_dag(circuit)
    base_folds = int((noise_factor - 1) // 2)
    fractional = ((noise_factor - 1) % 2) / 2

    fold_nodes = [
        node for node in dag.topological_op_nodes() if isinstance(node.op, DEFAULT_FOLDED_GATES)
    ]
    num_nodes = len(fold_nodes)

    num_extra_target = fractional * num_nodes
    if np.isclose(num_extra_target, 0):
        extra_indices: set[int] = set()
    else:
        num_extra = max(1, round(num_extra_target))
        extra_indices = _pick_extra_indices(num_nodes, num_extra, method, seed)

    for i, node in enumerate(fold_nodes):
        num_folds = base_folds + (1 if i in extra_indices else 0)
        if num_folds == 0:
            continue
        dag.substitute_node_with_dag(node, _folded_gate(node.op, num_folds))

    return dag_to_circuit(dag)


def _pick_extra_indices(
    num_nodes: int,
    num_extra: int,
    method: Literal["random", "front", "back"],
    seed: int | np.random.BitGenerator | None,
) -> set[int]:
    """Return indices of foldable nodes to fold one extra time."""
    if method == "front":
        return set(range(num_extra))
    if method == "back":
        return set(range(num_nodes - num_extra, num_nodes))
    rng = np.random.default_rng(seed)
    return set(rng.choice(num_nodes, num_extra, replace=False).tolist())


def _folded_gate(gate: Gate, num_folds: int) -> DAGCircuit:
    """Return a DAGCircuit that implements ``gate`` repeated ``2 * num_folds + 1`` times."""
    inverse = gate.inverse()
    qc = QuantumCircuit(gate.num_qubits, name=f"{gate.name}**{2 * num_folds + 1}")
    qc.append(gate, range(gate.num_qubits))
    for _ in range(num_folds):
        qc.append(inverse, range(gate.num_qubits))
        qc.append(gate, range(gate.num_qubits))
    return circuit_to_dag(qc)
