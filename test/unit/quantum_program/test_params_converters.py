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

"""Tests the decoder for the quantum program result model."""

from qiskit.circuit import QuantumCircuit
from qiskit_ibm_runtime import QuantumProgram
from qiskit_ibm_runtime.options_models import ExecutorOptions
from qiskit_ibm_runtime.quantum_program.params_converters import QUANTUM_PROGRAM_PARAMS_CONVERTERS
from ...ibm_test_case import IBMTestCase

from ddt import data, ddt


@ddt
class TestParamsConverters(IBMTestCase):
    """Tests for ParamConverters."""

    @data(*list(QUANTUM_PROGRAM_PARAMS_CONVERTERS))
    def test_round_trip(self, schema_version):
        """Test a round trip."""
        program = QuantumProgram(shots=100)
        program.append_circuit_item(QuantumCircuit(3))

        options = ExecutorOptions()

        converters = QUANTUM_PROGRAM_PARAMS_CONVERTERS[schema_version]
        encoded = converters.encoder(program, options).model_dump()
        decoded = converters.decoder(converters.model(**encoded))

        assert isinstance(decoded[0], QuantumProgram)
        assert decoded[1] == options
