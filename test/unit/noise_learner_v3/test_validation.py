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
from qiskit_ibm_runtime.models.backend_configuration import BackendConfiguration
from qiskit_ibm_runtime.fake_provider.backends import FakeAlgiers
from qiskit_ibm_runtime.exceptions import IBMInputValueError

from ...ibm_test_case import IBMTestCase


class TestValidation(IBMTestCase):
    """Tests the noise learner v3 validation."""

    def test_validate_options(self):
        """Test the function :func:`~qiskit_ibm_runtime/noise_learner_v3/validate_options`."""
        configuration = BackendConfiguration(
            backend_name="im_a_backend",
            backend_version="0.0",
            n_qubits=1e100,
            basis_gates=["rx"],
            gates=[],
            local=False,
            simulator=False,
            conditional=True,
            open_pulse=False,
            memory=True,
            coupling_map=[],
        )

        options = NoiseLearnerV3Options()
        options.post_selection = {"enable": True, "x_pulse_type": "rx"}
        validate_options(options=options, configuration=configuration)

        options.post_selection = {"enable": False, "x_pulse_type": "xslow"}
        validate_options(options=options, configuration=configuration)

        options.post_selection = {"enable": True, "x_pulse_type": "xslow"}
        with self.assertRaisesRegex(ValueError, "xslow"):
            validate_options(options=options, configuration=configuration)

    def test_validate_instruction(self):
        """Test the function :func:`~qiskit_ibm_runtime/noise_learner_v3/validate_instruction`."""
        target = FakeAlgiers().target

        circuit = QuantumCircuit(target.num_qubits)
        with circuit.box(annotations=[Twirl()]):
            circuit.cx(0, 1)
        with circuit.box(annotations=[]):
            circuit.noop(1)
        with circuit.box(annotations=[Twirl()]):
            circuit.measure_all()
        circuit.cx(0, 1)
        with circuit.box(annotations=[Twirl()]):
            circuit.cz(0, 1)
        block = QuantumCircuit(2)
        block.cx(0, 1)
        circuit.box(block, annotations=[Twirl()], qubits=[0, 13], clbits=[])
        with circuit.box(annotations=[Twirl()]):
            circuit.cx(0, 1)
            circuit.measure_all()

        # valid instructions
        validate_instruction(circuit.data[0], target)
        validate_instruction(circuit.data[2], target)

        # no box / box badly annotated
        with self.assertRaisesRegex(
            IBMInputValueError, "Found a box without a ``Twirl`` annotation"
        ):
            validate_instruction(circuit.data[1], target)
        with self.assertRaisesRegex(IBMInputValueError, "Expected a 'box' but found 'cx'"):
            validate_instruction(circuit.data[3], target)

        # ISA
        with self.assertRaisesRegex(IBMInputValueError, "instruction cz"):
            validate_instruction(circuit.data[4], target)
        with self.assertRaisesRegex(IBMInputValueError, r"instruction cx on qubits \(0, 13\)"):
            validate_instruction(circuit.data[5], target)

        # cannot be learned
        with self.assertRaisesRegex(IBMInputValueError, "cannot be learned"):
            validate_instruction(circuit.data[6], target)

        # unphysical
        circuit_unphysical = QuantumCircuit(2)
        with circuit_unphysical.box(annotations=[Twirl()]):
            circuit_unphysical.cx(0, 1)

        with self.assertRaisesRegex(
            IBMInputValueError, "Every qubit must be part of QuantumRegister"
        ):
            validate_instruction(circuit_unphysical.data[0], target)
