# This code is part of Qiskit.
#
# (C) Copyright IBM 2025-2026.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Tests for MidCircuitMeasure instruction."""

from ddt import data, ddt
from qiskit import QuantumCircuit, generate_preset_pass_manager
from qiskit.circuit import Instruction
from qiskit.providers.fake_provider import GenericBackendV2
from qiskit.transpiler.exceptions import TranspilerError

from qiskit_ibm_runtime.circuit import MeasureReset, MidCircuitMeasure, MidCircuitReset
from qiskit_ibm_runtime.fake_provider import FakeVigoV2

from ...ibm_test_case import IBMTestCase


@ddt
class TestMidCircuitMeasure(IBMTestCase):
    """Test MidCircuitMeasure instruction."""

    def test_instantiation(self):
        """Test default instantiation."""
        mcm = MidCircuitMeasure()
        assert mcm.base_class is MidCircuitMeasure
        assert isinstance(mcm, Instruction)
        assert mcm.name == "measure_2"
        assert mcm.num_qubits == 1
        assert mcm.num_clbits == 1

    @data("measure_3", "measure_reset")
    def test_instantiation_name(self, name):
        """Test instantiation with custom name."""
        mcm = MidCircuitMeasure(name)
        assert mcm.base_class is MidCircuitMeasure
        assert isinstance(mcm, Instruction)
        assert mcm.name == name
        assert mcm.num_qubits == 1
        assert mcm.num_clbits == 1

    def test_instantiation_invalid_name(self):
        """Test instantiation with an invalid name."""
        with self.assertRaises(ValueError):
            MidCircuitMeasure("invalid_name")

    def test_circuit_integration(self):
        """Test appending to circuit."""
        mcm = MidCircuitMeasure()
        qc = QuantumCircuit(1, 2)
        qc.append(mcm, [0], [0])
        qc.append(mcm, [0], [1])
        qc.reset(0)
        assert qc.data[0].operation is mcm
        assert qc.data[1].operation is mcm

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
        """Test default PM passes if measure_2 is in Target and does not modify the instruction.

        Test that default pass manager PASSES if measure_2 is in Target and doesn't modify the
        instruction.
        """
        mcm = MidCircuitMeasure()
        backend = GenericBackendV2(num_qubits=5, seed=0)
        backend.target.add_instruction(mcm, {(i,): None for i in range(5)})
        pm = generate_preset_pass_manager(backend=backend, seed_transpiler=0)
        qc = QuantumCircuit(1, 2)
        qc.append(mcm, [0], [0])
        transpiled = pm.run(qc)
        assert transpiled.data[0].operation.name == "measure_2"


class TestMidCircuitReset(IBMTestCase):
    """Test MidCircuitReset instruction."""

    def test_instantiation(self):
        """Test default instantiation."""
        mcr = MidCircuitReset()
        assert mcr.base_class is MidCircuitReset
        assert isinstance(mcr, Instruction)
        assert mcr.name == "reset_2"
        assert mcr.num_qubits == 1
        assert mcr.num_clbits == 0

    def test_instantiation_name(self):
        """Test instantiation with custom name."""
        mcr = MidCircuitReset("reset_3")
        assert mcr.base_class is MidCircuitReset
        assert isinstance(mcr, Instruction)
        assert mcr.name == "reset_3"
        assert mcr.num_qubits == 1
        assert mcr.num_clbits == 0

    def test_instantiation_invalid_name(self):
        """Test instantiation with an invalid name."""
        with self.assertRaises(ValueError):
            MidCircuitReset("invalid_name")

    def test_circuit_integration(self):
        """Test appending to circuit."""
        mcr = MidCircuitReset()
        qc = QuantumCircuit(1, 2)
        qc.append(mcr, [0])
        qc.append(mcr, [0])
        qc.reset(0)
        assert qc.data[0].operation is mcr
        assert qc.data[1].operation is mcr

    def test_transpiler_compat_without(self):
        """Test that default pass manager FAILS if reset_2 is not in Target."""
        mcr = MidCircuitReset()
        backend = FakeVigoV2()
        pm = generate_preset_pass_manager(backend=backend, seed_transpiler=0)
        qc = QuantumCircuit(1, 2)
        qc.append(mcr, [0])
        with self.assertRaises(TranspilerError):
            _ = pm.run(qc)

    def test_transpiler_compat_with(self):
        """Test default PM passes if reset_2 is in Target.

        Verifies it does not modify the instruction.
        """
        mcr = MidCircuitReset()
        backend = GenericBackendV2(num_qubits=5, seed=0)
        backend.target.add_instruction(mcr, {(i,): None for i in range(5)})
        pm = generate_preset_pass_manager(backend=backend, seed_transpiler=0)
        qc = QuantumCircuit(1, 2)
        qc.append(mcr, [0])
        transpiled = pm.run(qc)
        assert transpiled.data[0].operation.name == "reset_2"


class TestMeasureReset(IBMTestCase):
    """Test MeasureReset instruction."""

    def test_instantiation(self):
        """Test default instantiation."""
        mr = MeasureReset()
        assert mr.base_class is MeasureReset
        assert isinstance(mr, Instruction)
        assert mr.name == "measure_reset"
        assert mr.num_qubits == 1
        assert mr.num_clbits == 1

    def test_instantiation_name(self):
        """Test instantiation with custom name."""
        mr = MeasureReset("measure_reset_2")
        assert mr.base_class is MeasureReset
        assert isinstance(mr, Instruction)
        assert mr.name == "measure_reset_2"
        assert mr.num_qubits == 1
        assert mr.num_clbits == 1

    def test_instantiation_invalid_name(self):
        """Test instantiation with an invalid name."""
        with self.assertRaises(ValueError):
            MeasureReset("invalid_name")

    def test_circuit_integration(self):
        """Test appending to circuit."""
        mr = MeasureReset()
        qc = QuantumCircuit(1, 1)
        qc.append(mr, [0], [0])
        assert qc.data[0].operation is mr

    def test_transpiler_compat_without(self):
        """Test that default pass manager FAILS if measure_reset is not in Target."""
        mr = MeasureReset()
        backend = FakeVigoV2()
        pm = generate_preset_pass_manager(backend=backend, seed_transpiler=0)
        qc = QuantumCircuit(1, 1)
        qc.append(mr, [0], [0])
        with self.assertRaises(TranspilerError):
            _ = pm.run(qc)

    def test_transpiler_compat_with(self):
        """Test default PM passes if measure_reset is in Target.

        Verifies it does not modify the instruction.
        """
        mr = MeasureReset()
        backend = GenericBackendV2(num_qubits=5, seed=0)
        backend.target.add_instruction(mr, {(i,): None for i in range(5)})
        pm = generate_preset_pass_manager(backend=backend, seed_transpiler=0)
        qc = QuantumCircuit(1, 1)
        qc.append(mr, [0], [0])
        transpiled = pm.run(qc)
        assert transpiled.data[0].operation.name == "measure_reset"
