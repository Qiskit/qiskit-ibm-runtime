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

"""Tests the noise learner v3 validation."""

import pytest
from qiskit import QuantumCircuit
from samplomatic import Twirl

from qiskit_ibm_runtime.exceptions import IBMInputValueError
from qiskit_ibm_runtime.fake_provider.backends import FakeAlgiers
from qiskit_ibm_runtime.noise_learner_v3.validation import validate_instruction


class TestValidation:
    """Tests the noise learner v3 validation."""

    def test_validate_valid_instructions(self) -> None:
        """Test instruction validation for valid instructions."""
        target = FakeAlgiers().target
        circuit = QuantumCircuit(target.num_qubits)
        with circuit.box(annotations=[Twirl()]):
            circuit.cx(0, 1)
        with circuit.box(annotations=[Twirl()]):
            circuit.measure_all()

        validate_instruction(circuit.data[0], target)
        validate_instruction(circuit.data[1], target)

    def test_validate_instruction_bad_box(self) -> None:
        """Test that instruction validation raises when the box is badly annotated."""
        target = FakeAlgiers().target
        circuit = QuantumCircuit(target.num_qubits)
        with circuit.box(annotations=[]):
            circuit.noop(1)

        with pytest.raises(IBMInputValueError, match="Found a box without a ``Twirl`` annotation"):
            validate_instruction(circuit.data[0], target)

    def test_validate_instruction_no_box(self) -> None:
        """Test that instruction validation raises when there is no box."""
        target = FakeAlgiers().target
        circuit = QuantumCircuit(target.num_qubits)
        circuit.cx(0, 1)

        with pytest.raises(IBMInputValueError, match="Expected a 'box' but found 'cx'"):
            validate_instruction(circuit.data[0], target)

    def test_validate_instruction_isa_basis_gate(self) -> None:
        """Test that instruction validation raises for an operation that's not a basis gate."""
        target = FakeAlgiers().target
        circuit = QuantumCircuit(target.num_qubits)
        with circuit.box(annotations=[Twirl()]):
            circuit.cz(0, 1)

        with pytest.raises(IBMInputValueError, match="instruction cz"):
            validate_instruction(circuit.data[0], target)

    def test_validate_instruction_isa_connectivity(self) -> None:
        """Test that instruction validation raises for 2Q gates that violate the coupling map."""
        target = FakeAlgiers().target
        block = QuantumCircuit(2)
        block.cx(0, 1)
        circuit = QuantumCircuit(target.num_qubits)
        circuit.box(block, annotations=[Twirl()], qubits=[0, 13], clbits=[])

        with pytest.raises(IBMInputValueError, match=r"instruction cx on qubits \(0, 13\)"):
            validate_instruction(circuit.data[0], target)

    def test_validate_instruction_cannot_be_learned(self) -> None:
        """Test validation raises when the instruction doesn't match any learning protocol."""
        target = FakeAlgiers().target
        circuit = QuantumCircuit(target.num_qubits)
        with circuit.box(annotations=[Twirl()]):
            circuit.cx(0, 1)
            circuit.measure_all()

        with pytest.raises(IBMInputValueError, match="cannot be learned"):
            validate_instruction(circuit.data[0], target)

    def test_validate_instruction_unphysical(self) -> None:
        """Test validation raises when the qubits don't belong to the expected register."""
        target = FakeAlgiers().target
        circuit = QuantumCircuit(2)
        with circuit.box(annotations=[Twirl()]):
            circuit.cx(0, 1)

        with pytest.raises(IBMInputValueError, match="Every qubit must be part of QuantumRegister"):
            validate_instruction(circuit.data[0], target)
