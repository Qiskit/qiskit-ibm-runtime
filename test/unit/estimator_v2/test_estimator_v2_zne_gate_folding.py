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

"""Unit tests for the ZNE GateFolding pass used by the executor-based EstimatorV2."""

import unittest
from itertools import product

import ddt
from qiskit import QuantumCircuit
from qiskit.circuit.library import CXGate, CYGate, CZGate, ECRGate, RZGate, SwapGate
from qiskit.circuit.random import random_circuit
from qiskit.converters import circuit_to_dag
from qiskit.transpiler import generate_preset_pass_manager
from qiskit.transpiler.exceptions import TranspilerError

from qiskit_ibm_runtime.executor_estimator.zne.gate_folding import (
    DEFAULT_FOLDED_GATES,
    GateFolding,
)


@ddt.ddt
class TestGateFolding(unittest.TestCase):
    """Tests for GateFolding."""

    def test_pass_empty_circuit(self):
        """Test pass on an empty circuit."""
        circuit = QuantumCircuit(5)
        folder = GateFolding(CXGate, 3)
        [folded] = folder.fold(circuit)
        self.assertEqual(folded, circuit)

    def test_default_gate_set(self):
        """Default gate set matches the legacy ``stretched_gates``."""
        self.assertEqual(DEFAULT_FOLDED_GATES, (ECRGate, CXGate, CYGate, CZGate, SwapGate))

    @ddt.idata(product((CXGate, RZGate), (1, 1.3, 3, 4.1, 5)))
    @ddt.unpack
    def test_static_gate(self, gate, noise_factor):
        """Check that we end up with the correct number of gates within ±1."""
        circuit = random_circuit(5, 5, seed=321)
        circuit.measure_all()
        pm = generate_preset_pass_manager(basis_gates=["cx", "rz", "sx", "id"])
        circuit = pm.run(circuit)
        op_counts_initial = circuit_to_dag(circuit).count_ops(recurse=True)

        folder = GateFolding(gate, noise_factor)
        [tcircuit] = folder.fold(circuit)
        op_counts_final = circuit_to_dag(tcircuit).count_ops(recurse=False)

        self.assertEqual(len(op_counts_initial), len(op_counts_final))
        folded = "cx" if gate is CXGate else "rz"
        for op, count in op_counts_final.items():
            if op == folded:
                target = op_counts_initial[op] * noise_factor
                self.assertLessEqual(count, target + 1)
                self.assertGreaterEqual(count, target - 1)
            else:
                self.assertEqual(count, op_counts_initial[op])

    @ddt.data(CXGate, RZGate)
    def test_multi_noise_factor(self, gate):
        """Multiple noise factors in a single pass each produce correct counts."""
        noise_factors = [1, 1.5, 2]
        circuit = random_circuit(5, 5, seed=321)
        circuit.measure_all()
        pm = generate_preset_pass_manager(basis_gates=["cx", "rz", "sx", "id"])
        circuit = pm.run(circuit)
        op_counts_initial = circuit_to_dag(circuit).count_ops(recurse=True)

        folder = GateFolding(gate, noise_factors)
        tcircuits = folder.fold(circuit)
        self.assertEqual(len(tcircuits), len(noise_factors))

        folded = "cx" if gate is CXGate else "rz"
        for tcircuit, noise_factor in zip(tcircuits, noise_factors):
            op_counts_final = circuit_to_dag(tcircuit).count_ops(recurse=False)
            self.assertEqual(len(op_counts_initial), len(op_counts_final))
            for op, count in op_counts_final.items():
                if op == folded:
                    target = op_counts_initial[op] * noise_factor
                    self.assertLessEqual(count, target + 1)
                    self.assertGreaterEqual(count, target - 1)
                else:
                    self.assertEqual(count, op_counts_initial[op])

    @ddt.data(1, 3, 5)
    def test_parametric_gate(self, noise_factor):
        """Verify exact folded circuit for an RZ-only fold."""
        circuit = QuantumCircuit(2)
        circuit.sx(0)
        circuit.x(1)
        circuit.rz(0.1, 0)
        circuit.rz(0.2, 1)
        circuit.sx(0)
        circuit.x(1)

        folder = GateFolding(RZGate, noise_factor)
        [folded] = folder.fold(circuit)

        num_fold = int((noise_factor - 1) // 2)
        expected = QuantumCircuit(2)
        expected.sx(0)
        expected.x(1)
        expected.rz(0.1, 0)
        expected.rz(0.2, 1)
        for _ in range(num_fold):
            expected.rz(-0.1, 0)
            expected.rz(0.1, 0)
            expected.rz(-0.2, 1)
            expected.rz(0.2, 1)
        expected.sx(0)
        expected.x(1)
        self.assertEqual(folded, expected)

    def test_noise_factor_less_than_one_raises(self):
        """Noise factor < 1 raises TranspilerError at construction."""
        with self.assertRaises(TranspilerError):
            GateFolding(CXGate, noise_factors=0.5)
        with self.assertRaises(TranspilerError):
            GateFolding(CXGate, noise_factors=(1, 0.99))

    def test_method_front_picks_first_gates(self):
        """``method='front'`` selects probabilistic folds from the start of the DAG."""
        circuit = QuantumCircuit(2)
        for _ in range(4):
            circuit.cx(0, 1)

        # noise_factor=1.5: sampled_folds = 0.25, num_sampled = round(0.25*4) = 1.
        # 'front' picks the very first CX for the extra fold.
        folder = GateFolding(CXGate, noise_factors=1.5, method="front")
        [folded] = folder.fold(circuit)
        ops = list(folded.data)
        # First 3 instructions should be the folded first CX (CX, CX-inv, CX), rest are plain CX.
        self.assertEqual(ops[0].operation.name, "cx")
        self.assertEqual(ops[1].operation.name, "cx")
        self.assertEqual(ops[2].operation.name, "cx")
        self.assertEqual(ops[3].operation.name, "cx")
        self.assertEqual(folded.count_ops()["cx"], 6)

    def test_method_back_picks_last_gates(self):
        """``method='back'`` selects probabilistic folds from the end of the DAG."""
        circuit = QuantumCircuit(2)
        for _ in range(4):
            circuit.cx(0, 1)

        folder = GateFolding(CXGate, noise_factors=1.5, method="back")
        [folded] = folder.fold(circuit)
        self.assertEqual(folded.count_ops()["cx"], 6)

    def test_seed_reproducibility(self):
        """Same seed produces same probabilistic folds."""
        circuit = QuantumCircuit(2)
        for _ in range(6):
            circuit.cx(0, 1)
        [a] = GateFolding(CXGate, noise_factors=1.5, seed=42).fold(circuit)
        [b] = GateFolding(CXGate, noise_factors=1.5, seed=42).fold(circuit)
        self.assertEqual(a, b)

    def test_run_single_dag_path(self):
        """``run_single`` returns DAGs and accepts a DAG (legacy API surface)."""
        circuit = QuantumCircuit(2)
        circuit.cx(0, 1)
        circuit.cx(0, 1)
        dag = circuit_to_dag(circuit)
        dags = GateFolding(CXGate, noise_factors=(1, 3)).run_single(dag)
        self.assertEqual(len(dags), 2)
        self.assertEqual(dags[0].count_ops().get("cx", 0), 2)
        self.assertEqual(dags[1].count_ops().get("cx", 0), 6)

    def test_zne_noise_factor_metadata_stamped(self):
        """Folded DAGs carry ``metadata['zne_noise_factor']`` for legacy parity."""
        circuit = QuantumCircuit(2)
        circuit.cx(0, 1)
        dag = circuit_to_dag(circuit)
        dags = GateFolding(CXGate, noise_factors=(1, 3, 5)).run_single(dag)
        for d, expected_nf in zip(dags, (1, 3, 5)):
            self.assertEqual(d.metadata["zne_noise_factor"], expected_nf)


if __name__ == "__main__":
    unittest.main()
