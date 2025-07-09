# This code is part of Qiskit.
#
# (C) Copyright IBM 2025.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Tests for MidCircuitMeasure instruction."""

from qiskit import QuantumCircuit, generate_preset_pass_manager
from qiskit.circuit import Instruction
from qiskit.providers.fake_provider import GenericBackendV2
from qiskit.transpiler.exceptions import TranspilerError

from qiskit_ibm_runtime.circuit import MidCircuitMeasure
from qiskit_ibm_runtime.fake_provider import FakeVigoV2

from ...ibm_test_case import IBMTestCase


class TestMidCircuitMeasure(IBMTestCase):
    """Test MidCircuitMeasure instruction."""

    def test_instantiation(self):
        """Test default instantiation."""
        mcm = MidCircuitMeasure()
        self.assertIs(mcm.base_class, MidCircuitMeasure)
        self.assertIsInstance(mcm, Instruction)
        self.assertEqual(mcm.name, "measure_2")
        self.assertEqual(mcm.num_qubits, 1)
        self.assertEqual(mcm.num_clbits, 1)

    def test_instantiation_name(self):
        """Test instantiation with custom name."""
        with self.subTest("measure_3"):
            mcm = MidCircuitMeasure("measure_3")
            self.assertIs(mcm.base_class, MidCircuitMeasure)
            self.assertIsInstance(mcm, Instruction)
            self.assertEqual(mcm.name, "measure_3")
            self.assertEqual(mcm.num_qubits, 1)
            self.assertEqual(mcm.num_clbits, 1)

        with self.subTest("measure_reset"):
            mcm = MidCircuitMeasure("measure_reset")
            self.assertIs(mcm.base_class, MidCircuitMeasure)
            self.assertIsInstance(mcm, Instruction)
            self.assertEqual(mcm.name, "measure_reset")
            self.assertEqual(mcm.num_qubits, 1)
            self.assertEqual(mcm.num_clbits, 1)

        with self.subTest("invalid_name"):
            with self.assertRaises(ValueError):
                mcm = MidCircuitMeasure("invalid_name")

    def test_circuit_integration(self):
        """Test appending to circuit."""
        mcm = MidCircuitMeasure()
        qc = QuantumCircuit(1, 2)
        qc.append(mcm, [0], [0])
        qc.append(mcm, [0], [1])
        qc.reset(0)
        self.assertIs(qc.data[0].operation, mcm)
        self.assertIs(qc.data[1].operation, mcm)

    def test_transpiler_compat_without(self):
        """Test that default pass manager FAILS if measure_2 not in Target."""
        mcm = MidCircuitMeasure()
        backend = FakeVigoV2()
        pm = generate_preset_pass_manager(backend=backend, seed_transpiler=0)
        qc = QuantumCircuit(1, 2)
        qc.append(mcm, [0], [0])
        with self.assertRaises(TranspilerError):
            _ = pm.run(qc)

    def test_transpiler_compat_with(self):
        """Test that default pass manager PASSES if measure_2 is in Target
        and doesn't modify the instruction."""
        mcm = MidCircuitMeasure()
        backend = GenericBackendV2(num_qubits=5, seed=0)
        backend.target.add_instruction(mcm, {(i,): None for i in range(5)})
        pm = generate_preset_pass_manager(backend=backend, seed_transpiler=0)
        qc = QuantumCircuit(1, 2)
        qc.append(mcm, [0], [0])
        transpiled = pm.run(qc)
        self.assertEqual(transpiled.data[0].operation.name, "measure_2")
