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

"""Test the cliffordization pass."""

import numpy as np

from qiskit.circuit import QuantumCircuit
from qiskit.circuit.library import RXGate, RYGate, RZGate, HGate
from qiskit.transpiler.passmanager import PassManager

from qiskit_ibm_runtime.transpiler.passes import ToClifford

from .....ibm_test_case import IBMTestCase


class TestToClifford(IBMTestCase):
    """Tests the ToClifford pass."""

    def test_clifford_isa_circuit(self):
        """Test the pass on a Clifford circuit with ISA gates."""
        qc = QuantumCircuit(2)
        qc.id(0)
        qc.sx(0)
        qc.rz(0, 0)
        qc.rz(np.pi / 2, 0)
        qc.rz(np.pi, 0)
        qc.rz(3 * np.pi / 2, 0)
        qc.cx(0, 1)
        qc.cz(0, 1)
        qc.ecr(0, 1)

        pm = PassManager([ToClifford()])
        transformed = pm.run(qc)

        self.assertEqual(qc, transformed)

    def test_clifford_non_isa_circuit(self):
        """Test the pass on a Clifford circuit with ISA and non-ISA gates."""
        qc = QuantumCircuit(2)
        qc.id(0)
        qc.sx(0)
        qc.s(1)
        qc.h(1)
        qc.cx(0, 1)
        qc.cz(0, 1)
        qc.ecr(0, 1)

        pm = PassManager([ToClifford()])
        transformed = pm.run(qc)

        expected = QuantumCircuit(2)
        expected.id(0)
        expected.sx(0)
        expected.s(1)
        expected.h(1)
        expected.cx(0, 1)
        expected.cz(0, 1)
        expected.ecr(0, 1)

        self.assertEqual(expected, transformed)

    def test_non_clifford_isa_circuit(self):
        """Test the pass on a non-Clifford circuit with ISA gates."""
        qc = QuantumCircuit(2)
        qc.id(0)
        qc.sx(0)
        qc.rz(np.pi / 2 - 0.1, 0)
        qc.cx(0, 1)
        qc.cz(0, 1)
        qc.ecr(0, 1)

        pm = PassManager([ToClifford()])
        transformed = pm.run(qc)

        expected = QuantumCircuit(2)
        expected.id(0)
        expected.sx(0)
        expected.rz(np.pi / 2, 0)
        expected.cx(0, 1)
        expected.cz(0, 1)
        expected.ecr(0, 1)

        self.assertEqual(expected, transformed)

    def test_non_clifford_non_isa_circuit(self):
        """Test the pass on a non-Clifford circuit with ISA and non-ISA gates."""
        qc = QuantumCircuit(2)
        qc.id(0)
        qc.sx(0)
        qc.rz(np.pi / 2 - 0.1, 0)
        qc.rx(np.pi / 2 - 0.1, 1)
        qc.ry(np.pi / 2 - 0.1, 0)
        qc.cx(0, 1)
        qc.cz(0, 1)
        qc.ecr(0, 1)

        rules = [
            (RYGate, lambda x: HGate()),
            (RXGate, lambda x: RXGate(3 * np.pi / 2)),
        ]

        pm = PassManager([ToClifford(rules)])
        transformed = pm.run(qc)

        expected = QuantumCircuit(2)
        expected.id(0)
        expected.sx(0)
        expected.rz(np.pi / 2, 0)
        expected.rx(3 * np.pi / 2, 1)
        expected.h(0)
        expected.cx(0, 1)
        expected.cz(0, 1)
        expected.ecr(0, 1)

        self.assertEqual(expected, transformed)

    def test_overrides_default_rule_for_rz(self):
        """Test that rules allow specifying different replacement rules for RZ."""
        qc = QuantumCircuit(2)
        qc.id(0)
        qc.sx(0)
        qc.rz(np.pi / 2 - 0.1, 0)
        qc.cx(0, 1)
        qc.cz(0, 1)
        qc.ecr(0, 1)

        rules = [
            (RZGate, lambda x: HGate()),
        ]

        pm = PassManager([ToClifford(rules)])
        transformed = pm.run(qc)

        expected = QuantumCircuit(2)
        expected.id(0)
        expected.sx(0)
        expected.h(0)
        expected.cx(0, 1)
        expected.cz(0, 1)
        expected.ecr(0, 1)

        self.assertEqual(expected, transformed)

    def test_rules_for_clifford_are_ignored(self):
        """Test that rules for Clifford gates are ignored."""
        qc = QuantumCircuit(2)
        qc.h(0)

        rules = [
            (HGate, lambda x: RZGate(0)),
        ]

        pm = PassManager([ToClifford(rules)])
        transformed = pm.run(qc)

        expected = QuantumCircuit(2)
        expected.h(0)

        self.assertEqual(expected, transformed)

    def test_missing_rule(self):
        """Test that an error is raised when rules are missing."""
        qc = QuantumCircuit(2)
        qc.id(0)
        qc.sx(0)
        qc.rz(np.pi / 2 - 0.1, 0)
        qc.rx(np.pi / 2 - 0.1, 1)

        pm = PassManager([ToClifford()])
        with self.assertRaises(ValueError):
            pm.run(qc)

    def test_invalid_rule(self):
        """Test that an error is raised when rules lead to non-Clifford circuits."""
        qc = QuantumCircuit(2)
        qc.id(0)
        qc.sx(0)
        qc.rz(np.pi / 2 - 0.1, 0)
        qc.rx(np.pi / 2 - 0.1, 1)

        rules = [
            (RXGate, lambda x: RXGate(3 * np.pi / 8)),
        ]

        pm = PassManager([ToClifford(rules)])
        with self.assertRaises(ValueError):
            pm.run(qc)
