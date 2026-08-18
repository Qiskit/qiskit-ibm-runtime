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

"""Tests for XSlowGate instruction."""

from qiskit import QuantumCircuit, generate_preset_pass_manager
from qiskit.circuit import Gate
from qiskit.providers.fake_provider import GenericBackendV2
from qiskit.transpiler.exceptions import TranspilerError

from qiskit_ibm_runtime.circuit.library import XSlowGate
from qiskit_ibm_runtime.fake_provider import FakeVigoV2

from ...ibm_test_case import IBMTestCase


class TestXSlowGate(IBMTestCase):
    """Test XSlowGate instruction."""

    def test_instantiation(self):
        """Test default instantiation."""
        gate = XSlowGate()
        self.assertIs(gate.base_class, XSlowGate)
        self.assertIsInstance(gate, Gate)
        self.assertEqual(gate.name, "xslow")
        self.assertEqual(gate.num_qubits, 1)
        self.assertEqual(gate.num_clbits, 0)

    def test_circuit_integration(self):
        """Test appending XSlowGate to a circuit."""
        gate = XSlowGate()
        qc = QuantumCircuit(2)
        qc.append(gate, [0])
        qc.append(gate, [1])
        self.assertIs(qc.data[0].operation, gate)
        self.assertIs(qc.data[1].operation, gate)

    def test_transpiler_compat_without(self):
        """Test that the default pass manager fails if xslow is not inthe target."""
        gate = XSlowGate()
        backend = FakeVigoV2()
        pm = generate_preset_pass_manager(backend=backend, seed_transpiler=0)
        qc = QuantumCircuit(1)
        qc.append(gate, [0])
        with self.assertRaises(TranspilerError):
            pm.run(qc)

    def test_transpiler_compat_with(self):
        """Test that the default pass manager passes if xslow is in the target.

        Test also that the pass manager does not modify the instruction.
        """
        gate = XSlowGate()
        backend = GenericBackendV2(num_qubits=5, seed=0)
        backend.target.add_instruction(gate, {(i,): None for i in range(5)})
        pm = generate_preset_pass_manager(backend=backend, seed_transpiler=0)
        qc = QuantumCircuit(1)
        qc.append(gate, [0])
        transpiled = pm.run(qc)
        self.assertEqual(transpiled.data[0].operation.name, "xslow")
