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

"""Unit tests for the ZNE gate-folding helper used by the executor-based EstimatorV2."""

import unittest

import ddt
from qiskit import QuantumCircuit
from qiskit.circuit.library import CXGate, CYGate, CZGate, ECRGate, SwapGate
from qiskit.circuit.random import random_circuit
from qiskit.transpiler import generate_preset_pass_manager

from qiskit_ibm_runtime.executor_estimator.zne.gate_folding import (
    DEFAULT_FOLDED_GATES,
    fold_gates,
)


@ddt.ddt
class TestFoldGates(unittest.TestCase):
    """Tests for ``fold_gates``."""

    def test_default_gate_set(self):
        """Default gate set targets the standard 2-qubit ISA gates."""
        self.assertEqual(DEFAULT_FOLDED_GATES, (ECRGate, CXGate, CYGate, CZGate, SwapGate))

    def test_noise_factor_one_returns_copy(self):
        """``noise_factor=1`` returns a copy of the input, unchanged."""
        circuit = QuantumCircuit(2)
        circuit.cx(0, 1)
        circuit.cx(0, 1)
        folded = fold_gates(circuit, 1.0)
        self.assertEqual(folded, circuit)
        self.assertIsNot(folded, circuit)

    def test_empty_circuit(self):
        """Folding a circuit with no operations is a no-op."""
        circuit = QuantumCircuit(5)
        folded = fold_gates(circuit, 3.0)
        self.assertEqual(folded.count_ops(), circuit.count_ops())

    def test_no_foldable_gates(self):
        """Gates not in :data:`DEFAULT_FOLDED_GATES` are left alone."""
        circuit = QuantumCircuit(2)
        circuit.h(0)
        circuit.rz(0.1, 0)
        circuit.sx(1)
        folded = fold_gates(circuit, 3.0)
        self.assertEqual(folded.count_ops(), circuit.count_ops())

    @ddt.data(1, 1.3, 3, 4.1, 5)
    def test_count_within_one(self, noise_factor):
        """Folded CX count is within ±1 of ``noise_factor * initial_count``; non-CX unchanged."""
        circuit = random_circuit(5, 5, seed=321)
        circuit.measure_all()
        pm = generate_preset_pass_manager(basis_gates=["cx", "rz", "sx", "id"])
        circuit = pm.run(circuit)
        initial = circuit.count_ops()
        initial_cx = initial.get("cx", 0)
        if initial_cx == 0:
            self.skipTest("random circuit had no CX gates")

        folded = fold_gates(circuit, noise_factor)

        for op, count in folded.count_ops().items():
            if op == "cx":
                target = initial_cx * noise_factor
                self.assertLessEqual(count, target + 1)
                self.assertGreaterEqual(count, target - 1)
            else:
                self.assertEqual(count, initial[op])

    @ddt.data(3, 5, 7)
    def test_integer_fold_is_exact(self, noise_factor):
        """Integer noise factors fold every CX deterministically."""
        circuit = QuantumCircuit(2)
        for _ in range(3):
            circuit.cx(0, 1)
        folded = fold_gates(circuit, float(noise_factor))
        self.assertEqual(folded.count_ops()["cx"], 3 * noise_factor)

    def test_noise_factor_less_than_one_raises(self):
        """``noise_factor < 1`` raises ``ValueError``."""
        circuit = QuantumCircuit(2)
        circuit.cx(0, 1)
        with self.assertRaises(ValueError):
            fold_gates(circuit, 0.5)

    def test_method_front_picks_first_gates(self):
        """``method='front'`` selects probabilistic folds from the start of the DAG."""
        circuit = QuantumCircuit(2)
        for _ in range(4):
            circuit.cx(0, 1)

        # noise_factor=1.5 -> fractional=0.25, num_extra = round(0.25*4) = 1.
        # 'front' picks the very first CX for the extra fold (CX, CX-inv, CX), then 3 plain CX.
        folded = fold_gates(circuit, 1.5, method="front")
        self.assertEqual(folded.count_ops()["cx"], 6)
        for instr in list(folded.data)[:4]:
            self.assertEqual(instr.operation.name, "cx")

    def test_method_back_picks_last_gates(self):
        """``method='back'`` selects probabilistic folds from the end of the DAG."""
        circuit = QuantumCircuit(2)
        for _ in range(4):
            circuit.cx(0, 1)
        folded = fold_gates(circuit, 1.5, method="back")
        self.assertEqual(folded.count_ops()["cx"], 6)

    def test_seed_reproducibility(self):
        """Same seed produces the same probabilistic fold."""
        circuit = QuantumCircuit(2)
        for _ in range(6):
            circuit.cx(0, 1)
        a = fold_gates(circuit, 1.5, seed=42)
        b = fold_gates(circuit, 1.5, seed=42)
        self.assertEqual(a, b)


