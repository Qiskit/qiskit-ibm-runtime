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

import pytest

from qiskit.circuit import QuantumCircuit
from qiskit_ibm_runtime import QuantumProgram
from qiskit_ibm_runtime.options import ExecutorOptions
from qiskit_ibm_runtime.quantum_program.params_converters import QUANTUM_PROGRAM_PARAMS_CONVERTERS


@pytest.mark.parametrize("schema_version", ["v0.1", "v0.2"])
def test_round_trip(schema_version):
    """Test a round trip."""
    program = QuantumProgram(shots=100)
    program.append_circuit_item(QuantumCircuit(3))

    options = ExecutorOptions()

    converters = QUANTUM_PROGRAM_PARAMS_CONVERTERS[schema_version]
    decoded = converters.decoder(converters.encoder(program, options))

    assert isinstance(decoded[0], QuantumProgram)
    assert decoded[1] == options
