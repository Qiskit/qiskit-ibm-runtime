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

from qiskit_ibm_runtime.noise_learner_v3.validation import validate_options, validate_instruction
from qiskit_ibm_runtime.options import NoiseLearnerV3Options
from qiskit_ibm_runtime.models.backend_configuration import BackendConfiguration
from qiskit_ibm_runtime.fake_provider.backends import FakeAlgiers
from qiskit_ibm_runtime.exceptions import IBMInputValueError

from samplomatic import Twirl

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

        valid_options_ps_enabled = NoiseLearnerV3Options(
            post_selection={"enable": True, "x_pulse_type": "rx"}
        )
        validate_options(options=valid_options_ps_enabled, configuration=configuration)

        valid_options_ps_disabled = NoiseLearnerV3Options(
            post_selection={"enable": False, "x_pulse_type": "xslow"}
        )
        validate_options(options=valid_options_ps_disabled, configuration=configuration)

        invalid_options = NoiseLearnerV3Options(
            post_selection={"enable": True, "x_pulse_type": "xslow"}
        )
        with self.assertRaisesRegex(ValueError, "xslow"):
            validate_options(options=invalid_options, configuration=configuration)

    def test_validate_instruction(self):
        """Test the function :func:`~qiskit_ibm_runtime/noise_learner_v3/validate_instruction`."""
        backend = FakeAlgiers()
        target = backend.target

        circuit = QuantumCircuit(backend.num_qubits)
        with circuit.box(annotations=[Twirl()]):
            circuit.cz(0, 1)
        with circuit.box(annotations=[]):
            circuit.noop(1)
        with circuit.box(annotations=[Twirl()]):
            circuit.measure_all()
        circuit.cz(0, 1)
        with circuit.box(annotations=[Twirl()]):
            circuit.cx(0, 1)
        block1 = QuantumCircuit(2)
        block1.cz(0, 1)
        circuit.box(block1, annotations=[Twirl()], qubits=[0, 13], clbits=[])
        with circuit.box(annotations=[Twirl()]):
            circuit.rzz(1, 0, 1)

        # valid instructions
        validate_instruction(circuit.data[0], target)
        validate_instruction(circuit.data[2], target)

        # no box / box badly annotated
        with self.assertRaisesRegex(IBMInputValueError, "Found a box without a ``Twirl`` annotation"):
            validate_instruction(circuit.data[1], target)        
        with self.assertRaisesRegex(IBMInputValueError, "Expected a 'box' but found 'cz'"):
            validate_instruction(circuit.data[3], target)

        # ISA
        with self.assertRaisesRegex(IBMInputValueError, "instruction cx"):
            validate_instruction(circuit.data[4], target)
        with self.assertRaisesRegex(IBMInputValueError, "instruction cz on qubits 0, 13"):
            validate_instruction(circuit.data[5], target)

        # non-Clifford
        with self.assertRaisesRegex(IBMInputValueError, "cannot be learned"):
            validate_instruction(circuit.data[6], target)


        
