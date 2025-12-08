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

"""Tests the noise learner v3 validation."""

from qiskit import QuantumCircuit

from samplomatic import Twirl

from qiskit_ibm_runtime.noise_learner_v3.validation import validate_options, validate_instruction
from qiskit_ibm_runtime.options import NoiseLearnerV3Options
from qiskit_ibm_runtime.fake_provider.backends import FakeAlgiers, FakeFractionalBackend
from qiskit_ibm_runtime.exceptions import IBMInputValueError

from ...ibm_test_case import IBMTestCase


class TestValidation(IBMTestCase):
    """Tests the noise learner v3 validation."""

    def test_validate_options(self):
        """Test the validation of NLV3 options."""
        configuration = FakeFractionalBackend().configuration()

        options = NoiseLearnerV3Options()
        options.post_selection = {"enable": True, "x_pulse_type": "rx"}
        validate_options(options=options, configuration=configuration)

        options.post_selection = {"enable": False, "x_pulse_type": "xslow"}
        validate_options(options=options, configuration=configuration)

        options.post_selection = {"enable": True, "x_pulse_type": "xslow"}
        with self.assertRaisesRegex(ValueError, "xslow"):
            validate_options(options=options, configuration=configuration)

    def test_validate_valid_instructions(self):
        """Test instruction validation for valid instructions."""
        target = FakeAlgiers().target
        circuit = QuantumCircuit(target.num_qubits)
        with circuit.box(annotations=[Twirl()]):
            circuit.cx(0, 1)
        with circuit.box(annotations=[Twirl()]):
            circuit.measure_all()

        validate_instruction(circuit.data[0], target)
        validate_instruction(circuit.data[1], target)

    def test_validate_instruction_bad_box(self):
        """Test that instruction validation raises when the box is badly annotated."""
        target = FakeAlgiers().target
        circuit = QuantumCircuit(target.num_qubits)
        with circuit.box(annotations=[]):
            circuit.noop(1)

        with self.assertRaisesRegex(
            IBMInputValueError, "Found a box without a ``Twirl`` annotation"
        ):
            validate_instruction(circuit.data[0], target)

    def test_validate_instruction_no_box(self):
        """Test that instruction validation raises when there is no box."""
        target = FakeAlgiers().target
        circuit = QuantumCircuit(target.num_qubits)
        circuit.cx(0, 1)

        with self.assertRaisesRegex(IBMInputValueError, "Expected a 'box' but found 'cx'"):
            validate_instruction(circuit.data[0], target)

    def test_validate_instruction_isa_basis_gate(self):
        """Test that instruction validation raises for an operation that's not a basis gate."""
        target = FakeAlgiers().target
        circuit = QuantumCircuit(target.num_qubits)
        with circuit.box(annotations=[Twirl()]):
            circuit.cz(0, 1)

        with self.assertRaisesRegex(IBMInputValueError, "instruction cz"):
            validate_instruction(circuit.data[0], target)

    def test_validate_instruction_isa_connectivity(self):
        """Test that instruction validation raises for 2Q gates that violate the coupling map."""
        target = FakeAlgiers().target
        block = QuantumCircuit(2)
        block.cx(0, 1)
        circuit = QuantumCircuit(target.num_qubits)
        circuit.box(block, annotations=[Twirl()], qubits=[0, 13], clbits=[])

        with self.assertRaisesRegex(IBMInputValueError, r"instruction cx on qubits \(0, 13\)"):
            validate_instruction(circuit.data[0], target)

    def test_validate_instruction_cannot_be_learned(self):
        """Test that instruction validation raises when the instruction doesn't match any
        learning protocol."""
        target = FakeAlgiers().target
        circuit = QuantumCircuit(target.num_qubits)
        with circuit.box(annotations=[Twirl()]):
            circuit.cx(0, 1)
            circuit.measure_all()

        with self.assertRaisesRegex(IBMInputValueError, "cannot be learned"):
            validate_instruction(circuit.data[0], target)

    def test_validate_instruction_unphysical(self):
        """Test that instruction validation raises when the qubits don't belong to the expected
        register."""
        target = FakeAlgiers().target
        circuit = QuantumCircuit(2)
        with circuit.box(annotations=[Twirl()]):
            circuit.cx(0, 1)

        with self.assertRaisesRegex(
            IBMInputValueError, "Every qubit must be part of QuantumRegister"
        ):
            validate_instruction(circuit.data[0], target)
