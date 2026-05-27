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

"""Unit tests for the ZNE :class:`GateFolding` transpiler pass."""

import unittest
from typing import Any

import ddt
import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit import Parameter
from qiskit.circuit.library import CXGate, CYGate, CZGate, ECRGate, SwapGate
from qiskit.converters import circuit_to_dag, dag_to_circuit
from qiskit.quantum_info import Operator
from qiskit.transpiler import PassManager

from qiskit_ibm_runtime.executor_estimator.zne import DEFAULT_FOLDED_GATES, GateFolding


def fold(circuit: QuantumCircuit, noise_factor: float, **kwargs: Any) -> QuantumCircuit:
    """Test helper: run ``GateFolding`` via a one-pass PassManager."""
    return PassManager([GateFolding(noise_factor, **kwargs)]).run(circuit)


@ddt.ddt
class TestGateFolding(unittest.TestCase):
    """Tests for ``GateFolding``."""

    def test_default_gate_set(self):
        """Default gate set targets the standard 2-qubit ISA gates."""
        self.assertEqual(DEFAULT_FOLDED_GATES, (ECRGate, CXGate, CYGate, CZGate, SwapGate))

    def test_noise_factor_one_returns_equal_circuit(self):
        """``noise_factor=1`` leaves the circuit unchanged in content."""
        circuit = QuantumCircuit(2)
        circuit.cx(0, 1)
        circuit.cx(0, 1)
        folded = fold(circuit, 1.0)
        self.assertEqual(folded, circuit)

    def test_empty_circuit(self):
        """Folding a circuit with no operations is a no-op."""
        circuit = QuantumCircuit(5)
        folded = fold(circuit, 3.0)
        self.assertEqual(folded.count_ops(), circuit.count_ops())

    def test_no_foldable_gates(self):
        """Gates not in :data:`DEFAULT_FOLDED_GATES` are left alone."""
        circuit = QuantumCircuit(2)
        circuit.h(0)
        circuit.rz(0.1, 0)
        circuit.sx(1)
        folded = fold(circuit, 3.0)
        self.assertEqual(folded.count_ops(), circuit.count_ops())

    @ddt.data(1, 1.3, 3, 4.1, 5)
    def test_count_within_one(self, noise_factor):
        """Folded CX count is within ±1 of ``noise_factor * initial_count``; non-CX unchanged."""
        circuit = QuantumCircuit(3)
        circuit.h(0)
        circuit.cx(0, 1)
        circuit.rz(0.3, 1)
        circuit.cx(1, 2)
        circuit.sx(2)
        circuit.cx(0, 2)
        circuit.cx(1, 2)
        initial = circuit.count_ops()
        initial_cx = initial["cx"]

        folded = fold(circuit, noise_factor)

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
        folded = fold(circuit, float(noise_factor))
        self.assertEqual(folded.count_ops()["cx"], 3 * noise_factor)

    def test_noise_factor_less_than_one_raises(self):
        """``noise_factor < 1`` raises ``ValueError`` at pass construction."""
        with self.assertRaises(ValueError):
            GateFolding(0.5)

    def test_method_front_picks_first_gates(self):
        """``method='front'`` selects probabilistic folds from the start of the DAG."""
        circuit = QuantumCircuit(2)
        for _ in range(4):
            circuit.cx(0, 1)

        # noise_factor=1.5 -> fractional=0.25, num_extra = round(0.25*4) = 1.
        # 'front' picks the very first CX for the extra fold (CX, CX-inv, CX), then 3 plain CX.
        folded = fold(circuit, 1.5, method="front")
        self.assertEqual(folded.count_ops()["cx"], 6)
        for instr in list(folded.data)[:4]:
            self.assertEqual(instr.operation.name, "cx")

    def test_method_back_picks_last_gates(self):
        """``method='back'`` selects probabilistic folds from the end of the DAG."""
        circuit = QuantumCircuit(2)
        for _ in range(4):
            circuit.cx(0, 1)
        folded = fold(circuit, 1.5, method="back")
        self.assertEqual(folded.count_ops()["cx"], 6)

    def test_seed_reproducibility(self):
        """Two pass instances with the same seed produce the same probabilistic fold."""
        circuit = QuantumCircuit(2)
        for _ in range(6):
            circuit.cx(0, 1)
        a = fold(circuit, 1.5, seed=42)
        b = fold(circuit, 1.5, seed=42)
        self.assertEqual(a, b)

    def test_pass_instance_is_reusable(self):
        """Running the same pass instance twice yields the same result (no state leaks)."""
        circuit = QuantumCircuit(2)
        for _ in range(6):
            circuit.cx(0, 1)
        pm = PassManager([GateFolding(1.5, seed=42)])
        self.assertEqual(pm.run(circuit), pm.run(circuit))

    def test_run_on_dag_directly(self):
        """The pass also works invoked directly on a DAG, without a PassManager."""
        circuit = QuantumCircuit(2)
        circuit.cx(0, 1)
        circuit.cx(0, 1)
        folded_dag = GateFolding(3.0).run(circuit_to_dag(circuit))
        self.assertEqual(dag_to_circuit(folded_dag).count_ops()["cx"], 6)

    def test_composes_in_passmanager_with_other_passes(self):
        """``GateFolding`` plays nicely with another pass in a PassManager stack."""
        from qiskit.transpiler.passes import Optimize1qGates  # 1q-only pass; leaves CX alone

        circuit = QuantumCircuit(2)
        circuit.cx(0, 1)
        circuit.cx(0, 1)
        pm = PassManager([Optimize1qGates(), GateFolding(3.0)])
        self.assertEqual(pm.run(circuit).count_ops()["cx"], 6)

    def test_same_pass_instance_on_different_circuits(self):
        """One pass instance can be applied to different circuits with independent results."""
        pm = PassManager([GateFolding(3.0)])
        qc1 = QuantumCircuit(2)
        qc1.cx(0, 1)
        qc2 = QuantumCircuit(2)
        qc2.cx(0, 1)
        qc2.cx(0, 1)
        self.assertEqual(pm.run(qc1).count_ops()["cx"], 3)
        self.assertEqual(pm.run(qc2).count_ops()["cx"], 6)

    def test_fractional_noise_factor_no_foldable_gates(self):
        """A fractional noise factor on a circuit with no foldable gates is a no-op."""
        # Regression guard: fractional logic must not try to pick extra indices from an empty set.
        circuit = QuantumCircuit(2)
        circuit.h(0)
        circuit.h(1)
        folded = fold(circuit, 1.5)
        self.assertEqual(folded.count_ops(), circuit.count_ops())

    def test_run_on_dag_mutates_input(self):
        """Calling ``.run`` directly on a DAG mutates and returns that same DAG."""
        # PassManager protects callers by copying, but a bare ``.run(dag)`` does not.
        circuit = QuantumCircuit(2)
        circuit.cx(0, 1)
        circuit.cx(0, 1)
        dag = circuit_to_dag(circuit)
        out = GateFolding(3.0).run(dag)
        self.assertIs(out, dag)
        self.assertEqual(dag_to_circuit(dag).count_ops()["cx"], 6)

    def test_parameterized_circuit_preserves_parameters(self):
        """Folding leaves unbound parameters in place (foldable gates are non-parametric)."""
        theta = Parameter("theta")
        circuit = QuantumCircuit(2)
        circuit.rz(theta, 0)
        circuit.cx(0, 1)
        circuit.cx(0, 1)
        folded = fold(circuit, 3.0)
        self.assertEqual(folded.parameters, circuit.parameters)
        self.assertEqual(folded.count_ops()["cx"], 6)
        self.assertEqual(folded.count_ops()["rz"], 1)

    def test_does_not_recurse_into_control_flow_blocks(self):
        """Gates nested inside ``if_else`` blocks are not folded; outer gates still fold."""
        # Control-flow recursion would require a separate pass (e.g. ``ControlFlowOp`` handling);
        # this test documents that the bare pass does not recurse.
        circuit = QuantumCircuit(2, 1)
        circuit.cx(0, 1)
        circuit.measure(0, 0)
        with circuit.if_test((circuit.clbits[0], 1)):
            circuit.cx(0, 1)

        folded = fold(circuit, 3.0)
        self.assertEqual(folded.count_ops()["cx"], 3)  # outer CX: 1 -> 3
        self.assertEqual(folded.count_ops()["if_else"], 1)
        # Inner block is unchanged: still exactly one CX inside.
        if_else_instr = next(instr for instr in folded.data if instr.operation.name == "if_else")
        inner_body = if_else_instr.operation.blocks[0]
        self.assertEqual(inner_body.count_ops()["cx"], 1)

    @ddt.data(3.0, 5.0, 7.0)
    def test_unitary_equivalence(self, noise_factor):
        """Folded circuit is unitarily equivalent to the original for any odd-integer factor."""
        circuit = QuantumCircuit(2)
        circuit.cx(0, 1)
        circuit.swap(0, 1)
        circuit.cz(0, 1)
        folded = fold(circuit, noise_factor)
        self.assertTrue(Operator(circuit).equiv(Operator(folded)))

    def test_seed_accepts_numpy_generator(self):
        """A ``np.random.Generator`` instance is accepted as ``seed`` (per the type hint)."""
        circuit = QuantumCircuit(2)
        for _ in range(4):
            circuit.cx(0, 1)
        a = fold(circuit, 1.5, seed=np.random.default_rng(123))
        b = fold(circuit, 1.5, seed=np.random.default_rng(123))
        self.assertEqual(a, b)

    @ddt.data(CXGate, CYGate, CZGate, ECRGate, SwapGate)
    def test_folds_each_default_gate_type(self, gate_cls):
        """Each gate type in :data:`DEFAULT_FOLDED_GATES` is folded by the pass."""
        circuit = QuantumCircuit(2)
        circuit.append(gate_cls(), [0, 1])
        folded = fold(circuit, 3.0)
        self.assertEqual(folded.count_ops()[gate_cls().name], 3)
        self.assertTrue(Operator(circuit).equiv(Operator(folded)))
