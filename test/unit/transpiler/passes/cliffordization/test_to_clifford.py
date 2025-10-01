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
from qiskit.transpiler.passmanager import PassManager

from qiskit_ibm_runtime.transpiler.passes import ConvertISAToClifford

from .....ibm_test_case import IBMTestCase


class TestConvertISAToClifford(IBMTestCase):
    """Tests the ConvertISAToClifford pass."""

    def test_clifford_isa_circuit(self):
        """Test the pass on a Clifford circuit with ISA gates."""
        qc = QuantumCircuit(2, 2)
        qc.id(0)
        qc.sx(0)
        qc.barrier()
        qc.measure(0, 1)
        qc.rz(0, 0)
        qc.rz(np.pi / 2, 0)
        qc.rz(np.pi, 0)
        qc.rz(3 * np.pi / 2, 0)
        qc.cx(0, 1)
        qc.cz(0, 1)
        qc.ecr(0, 1)

        pm = PassManager([ConvertISAToClifford()])
        transformed = pm.run(qc)

        self.assertEqual(qc, transformed)

    def test_non_clifford_isa_circuits(self):
        """Test the pass on a non-Clifford circuit with ISA gates."""
        qc = QuantumCircuit(2, 2)
        qc.id(0)
        qc.sx(0)
        qc.barrier()
        qc.measure(0, 1)
        qc.rz(0, 0)
        qc.rzz(np.pi / 3, 0, 1)
        qc.rx(np.pi / 3, 0)
        qc.rz(np.pi / 2 - 0.1, 0)
        qc.rz(np.pi, 0)
        qc.rz(3 * np.pi / 2 + 0.1, 1)
        qc.cx(0, 1)
        qc.cz(0, 1)
        qc.ecr(0, 1)

        pm = PassManager([ConvertISAToClifford()])
        transformed = pm.run(qc)

        expected = QuantumCircuit(2, 2)
        expected.id(0)
        expected.sx(0)
        expected.barrier()
        expected.measure(0, 1)
        expected.rz(0, 0)
        expected.rzz(np.pi / 2, 0, 1)
        expected.rx(np.pi / 2, 0)
        expected.rz(np.pi / 2, 0)
        expected.rz(np.pi, 0)
        expected.rz(3 * np.pi / 2, 1)
        expected.cx(0, 1)
        expected.cz(0, 1)
        expected.ecr(0, 1)

        self.assertEqual(transformed, expected)

    def test_error_clifford_non_isa_circuit(self):
        """Test that the pass errors when run on a Clifford circuit with non-ISA gates."""
        qc = QuantumCircuit(2)
        qc.id(0)
        qc.sx(0)
        qc.s(1)
        qc.h(1)
        qc.cx(0, 1)
        qc.cz(0, 1)
        qc.ecr(0, 1)

        pm = PassManager([ConvertISAToClifford()])
        with self.assertRaises(ValueError):
            pm.run(qc)

    def test_error_non_clifford_isa_circuit(self):
        """Test that the pass errors when run on a non-Clifford circuit with ISA gates."""
        qc = QuantumCircuit(2)
        qc.id(0)
        qc.sx(0)
        qc.ry(np.pi / 2 - 0.1, 0)
        qc.cx(0, 1)
        qc.cz(0, 1)
        qc.ecr(0, 1)

        pm = PassManager([ConvertISAToClifford()])
        with self.assertRaises(ValueError):
            pm.run(qc)

    def test_error_reset(self):
        """Test that the pass errors when run on circuits with resets."""
        qc = QuantumCircuit(2)
        qc.x(1)
        qc.barrier(0)
        qc.reset(1)
        qc.ry(np.pi / 2 - 0.1, 1)

        pm = PassManager([ConvertISAToClifford()])
        with self.assertRaises(ValueError):
            pm.run(qc)
