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

import logging
from collections.abc import Sequence
from copy import deepcopy
from functools import lru_cache
from itertools import repeat
from numbers import Number
from time import time
from typing import Literal

import numpy as np
from qiskit.circuit import Gate, QuantumCircuit
from qiskit.circuit.library import CXGate, CYGate, CZGate, ECRGate, SwapGate
from qiskit.converters import circuit_to_dag, dag_to_circuit
from qiskit.dagcircuit import DAGCircuit
from qiskit.transpiler.exceptions import TranspilerError

LOG = logging.getLogger(__name__)


DEFAULT_FOLDED_GATES: tuple[type, ...] = (ECRGate, CXGate, CYGate, CZGate, SwapGate)
"""Default 2-qubit gate types to fold."""


class GateFolding:
    r"""A transpiler pass to replace gates with folded repetitions.

    A folded gate is repeated as :math:`U\mapsto U.(U^\dagger.U)^{n}` where
    :math:`n` is the number of folds. The intended number of folds is
    represented by a *noise factor*  :math:`F >= 1`, where the number of folds
    is given by :math:`n = (F-1)/2`. If the number of folds is not an integer,
    probabilistic sampling is applied to randomly fold a subset of gates one
    extra time so that the noise factor averages to the desired value.
    """

    def __init__(
        self,
        gates: type | Sequence[type] = DEFAULT_FOLDED_GATES,
        noise_factors: float | Sequence[float] = 1.0,
        method: Literal["random", "front", "back"] = "random",
        seed: np.random.BitGenerator | None = None,
    ):
        """GateFolding pass.

        Args:
            gates: One or more circuit instruction types to replace with a
                   repeated number of the same gate.
            noise_factors: the target noise factors for folding gates. Must be >= 1.
            method: A method for selecting sampled nodes. Can be ``"random"`` for
                randomly selecting N folded nodes, ``"front"``/``"back"`` for taking
                the first/last N folded nodes in the topologically ordered DAG.
            seed: Optional, seed or BitGenerator for random number generation when
                  doing probabilistic folding.

        Raises:
            TranspilerError: If the noise factor is not >= 1.
        """
        if isinstance(gates, type):
            self._gates = (gates,)
        else:
            self._gates = tuple(gates)
        self._method = method
        self._seed = seed
        if isinstance(noise_factors, Number):
            noise_factors = (noise_factors,)
        self._noise_factors = tuple(noise_factors)
        for noise_factor in self._noise_factors:
            if noise_factor < 1:
                raise TranspilerError(f"noise_factors ({self._noise_factors}) must be >= 1.")

    def run_single(self, dag: DAGCircuit) -> list[DAGCircuit]:
        """Fold ``dag`` once per configured noise factor."""
        LOG.debug(
            "Start gate folding pass with noise factors=%s, gates=%s",
            self._noise_factors,
            self._gates,
        )
        skip_copy = len(self._noise_factors) == 1
        sampled_node_indices = self._choose_sampled_nodes(dag)
        folded_dags = []
        t_start = time()
        for noise_factor in self._noise_factors:
            # Avoid DAG deepcopy when there is only 1 noise factor
            new_dag = dag if skip_copy else deepcopy(dag)
            new_dag = self._fold_nodes_greedy(new_dag, noise_factor, sampled_node_indices)
            folded_dags.append(new_dag)
        LOG.debug("Folding pass took: %s s", t_start - time())
        return folded_dags

    def fold(self, circuit: QuantumCircuit) -> list[QuantumCircuit]:
        """Fold ``circuit`` once per configured noise factor.

        Convenience wrapper around :meth:`run_single` that takes and returns
        :class:`~qiskit.circuit.QuantumCircuit` objects.
        """
        dag = circuit_to_dag(circuit)
        return [dag_to_circuit(folded) for folded in self.run_single(dag)]

    def _fold_nodes_greedy(
        self, dag: DAGCircuit, noise_factor: float, sampled_node_indices: np.ndarray
    ) -> DAGCircuit:
        """Greedy algorithm to probabilistically fold nodes.

        This needs to know the number of nodes in the circuit and samples
        a number for folding to get as close to the target noise factor as
        possible. It will not work for dynamical circuits.
        """
        LOG.debug("Folding with noise_factor=%s", noise_factor)

        if np.isclose(noise_factor, 1):
            # If noise factor is 1 dag is unchanged
            dag.metadata["zne_noise_factor"] = noise_factor  # for legacy post-processing
            return dag

        # Determine contant fold number and sampled fold probability
        base_folds = int((noise_factor - 1) // 2)
        sampled_folds = ((noise_factor - 1) % 2) / 2

        # Get the folded nodes in topological order.
        fold_nodes = [
            node for node in dag.topological_op_nodes() if isinstance(node.op, self._gates)
        ]
        num_nodes = len(fold_nodes)
        repeated_gates = set()

        # No sampling required
        num_sampled = sampled_folds * num_nodes
        if np.isclose(num_sampled, 0):
            num_folds = repeat(base_folds, num_nodes)
            total_folds = base_folds * num_nodes
        else:
            num_sampled = max(1, round(num_sampled))
            rand_folds = sampled_node_indices[:num_sampled]
            num_folds = np.tile(base_folds, num_nodes)
            num_folds[rand_folds] += 1
            total_folds = np.sum(num_folds)
        LOG.debug("Number of total folds: %s", total_folds)

        for node, gate_folds in zip(fold_nodes, num_folds):
            # TODO: We may need to pass in basis gates kwarg if the folded gate
            # inverse is not the same type as the gate (eg not self inverse
            # like CX, CZ, ECR, or not change in parameter value like RZ)
            if gate_folds == 0:
                continue
            cls = type(node.op)
            try:
                node_dag = _folded_gate_cached(cls, gate_folds)
            except TypeError:
                node_dag = _folded_gate(node.op, gate_folds)
            repeated_gates.add(cls)
            dag.substitute_node_with_dag(node, node_dag)

        # Calculate the sampled noise factor
        if num_nodes == 0:
            sampled_noise_factor = noise_factor
        else:
            sampled_noise_factor = 1 + 2 * total_folds / num_nodes
        LOG.debug("Sampled noise factor is %s", sampled_noise_factor)
        LOG.debug("Repeated gates are %s", repeated_gates)
        dag.metadata["zne_noise_factor"] = noise_factor  # for legacy post-processing
        return dag

    def _choose_sampled_nodes(self, dag: DAGCircuit) -> np.ndarray:
        """Greedy algorithm for sampling probabilistically folded nodes.

        Args:
            num_nodes: The total number of folded nodes in the input dag.

        Returns:
            A 1D array of the folded nodes sampled for probabilistic folding.
        """
        num_nodes = sum(len(dag.op_nodes(gate)) for gate in self._gates)

        # Determine constant fold number and sampled fold probability
        sampled_folds = [((nf - 1) % 2) / 2 for nf in self._noise_factors]

        # If at least 1 noise factor requires sampling we find the max sampled
        # noise factor and use that for sampling so noise factors will
        # reuse sampled gates in higher noise factors rather than sampling
        # each noise factor completely independently
        num_sampled = [sampled * num_nodes for sampled in sampled_folds]
        if np.allclose(num_sampled, 0):
            # No sampling needed
            return np.empty(0, dtype=int)

        max_sampled = max(1, round(max(num_sampled)))
        if self._method == "front":
            selected = np.arange(max_sampled)
        elif self._method == "back":
            selected = np.arange(num_nodes - max_sampled, num_nodes)
        else:
            # Random selection
            rng = np.random.default_rng(self._seed)
            selected = rng.choice(num_nodes, max_sampled, replace=False)
        return selected


@lru_cache
def _folded_gate_cached(gate_type: type, num_folds: int = 0) -> DAGCircuit:
    """Cached folded DAGCircuit for singleton-like gates"""
    return _folded_gate(gate_type(), num_folds=num_folds)


def _folded_gate(gate: Gate, num_folds: int = 0) -> DAGCircuit:
    """Return the folded gate DAGCircuit for node replacement in a DAGCircuit"""
    name = f"{gate.name}**{2 * num_folds + 1}"
    inverse = gate.inverse()
    qc = QuantumCircuit(gate.num_qubits, name=name)
    qc.append(gate, range(gate.num_qubits))
    for _ in range(num_folds):
        qc.append(inverse, range(gate.num_qubits))
        qc.append(gate, range(gate.num_qubits))
    return circuit_to_dag(qc)
