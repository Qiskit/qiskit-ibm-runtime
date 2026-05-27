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

"""Transpiler pass that scales gate noise by gate folding."""

from __future__ import annotations

from typing import Literal

import numpy as np
from qiskit.circuit import Gate, QuantumCircuit
from qiskit.circuit.library import CXGate, CYGate, CZGate, ECRGate, SwapGate
from qiskit.converters import circuit_to_dag
from qiskit.dagcircuit import DAGCircuit
from qiskit.transpiler.basepasses import TransformationPass


SUPPORTED_FOLDED_GATES: tuple[type, ...] = (ECRGate, CXGate, CYGate, CZGate, SwapGate)
"""2-qubit gate types supported for folding."""


class GateFolding(TransformationPass):
    r"""Transpiler pass that folds 2-qubit gates to amplify their noise.

    Each foldable gate :math:`U` is replaced by :math:`U(U^\dagger U)^n` where
    :math:`n = (F - 1) / 2` for noise factor :math:`F \geq 1`. When ``noise_factor``
    is not such that every gate folds the same number of times, a subset of gates
    is folded one extra time; ``method`` controls which subset.

    Only gates in :data:`~qiskit_ibm_runtime.executor_estimator.zne.SUPPORTED_FOLDED_GATES`
    will be folded.
    """

    def __init__(
        self,
        noise_factor: float,
        method: Literal["random", "front", "back"] = "random",
        seed: int | np.random.BitGenerator | np.random.Generator | None = None,
    ):
        """Initialize the pass.

        Args:
            noise_factor: Target noise factor (``>= 1``).
            method: How to choose a subset of gates to fold an additional time
                to implement noise factors other than even integers. The gates
                may be chosen from the ``front`` or ``back`` of the circuit, or
                uniformly at ``random``.
            seed: Random seed/generator for selecting gates at random.

        Raises:
            ValueError: If ``noise_factor`` is less than 1.
        """
        super().__init__()
        if noise_factor < 1:
            raise ValueError(f"noise_factor must be >= 1, got {noise_factor}.")
        self.noise_factor = noise_factor
        self.method = method
        self.seed = seed

    def run(self, dag: DAGCircuit) -> DAGCircuit:
        """Fold ``dag`` in place and return it."""
        if np.isclose(self.noise_factor, 1):
            return dag

        base_folds = int((self.noise_factor - 1) // 2)
        fractional = ((self.noise_factor - 1) % 2) / 2
        fold_nodes = [
            n for n in dag.topological_op_nodes() if isinstance(n.op, SUPPORTED_FOLDED_GATES)
        ]
        num_nodes = len(fold_nodes)

        extra_indices: set[int] = set()
        num_extra_target = fractional * num_nodes
        if not np.isclose(num_extra_target, 0):
            num_extra = max(1, round(num_extra_target))
            if self.method == "front":
                extra_indices = set(range(num_extra))
            elif self.method == "back":
                extra_indices = set(range(num_nodes - num_extra, num_nodes))
            else:
                rng = np.random.default_rng(self.seed)
                extra_indices = set(rng.choice(num_nodes, num_extra, replace=False).tolist())

        for i, node in enumerate(fold_nodes):
            folds = base_folds + (i in extra_indices)
            if folds:
                dag.substitute_node_with_dag(node, _folded_gate(node.op, folds))
        return dag


def _folded_gate(gate: Gate, num_folds: int) -> DAGCircuit:
    """Return a DAGCircuit that implements ``gate`` repeated ``2 * num_folds + 1`` times."""
    qc = QuantumCircuit(gate.num_qubits, name=f"{gate.name}**{2 * num_folds + 1}")
    qc.append(gate, range(gate.num_qubits))
    for _ in range(num_folds):
        qc.append(gate.inverse(), range(gate.num_qubits))
        qc.append(gate, range(gate.num_qubits))
    return circuit_to_dag(qc)
