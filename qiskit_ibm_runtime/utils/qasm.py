# This code is part of Qiskit.
#
# (C) Copyright IBM 2023.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Utility funcitions for OpenQASM support."""
import logging
import re
from typing import Dict, Iterable, Sequence, Union

from qiskit.circuit import QuantumCircuit
from qiskit.qasm3 import loads as qasm3_loads

INVALID_QASM_VERSION_MESSAGE = (
    "OpenQASM version invalid or not specified in program, will use OpenQASM 3."
)

QuantumProgram = Union[QuantumCircuit, str]

logger = logging.getLogger(__name__)


def str_to_quantum_circuit(program: str) -> QuantumCircuit:
    """Converts a QASM program to a QuantumCircuit object. Depending on the
    OpenQASM version of the program, it will use either
    `QuantumCircuit.from_qasm_str` or `qiskit.qasm3.loads`.
    If no OpenQASM version is specified in the header of the program, then it's
    assumed to be an OpenQASM3 program.

    Args:
        program: a OpenQASM program as a string

    Returns:
        QuantumCircuit: the input OpenQASM program as a quantum circuit object

    """
    result = re.search(r"OPENQASM\s+(\d+)(\.(\d+))*", program)
    if result is None:
        # Issue a warning and try using OpenQASM3 if version was invalid or not specified
        logger.warning(INVALID_QASM_VERSION_MESSAGE)
        return qasm3_loads(program)
    else:
        qasm_version = result.group(1)
        if float(qasm_version) == 2:
            # OpenQASM2
            return QuantumCircuit.from_qasm_str(program)
        else:  # version 3 and other versions
            # use default OpenQASM3 loads
            return qasm3_loads(program)


def parse_qasm_circuits(
    circuits: Union[Sequence[QuantumProgram], QuantumProgram]
) -> Iterable[QuantumCircuit]:
    """Convert from QASM to QauntumCircuit, if needed."""

    if isinstance(circuits, str):
        circuits = [str_to_quantum_circuit(circuits)]
    elif isinstance(circuits, Dict):
        circuits = {
            k: (str_to_quantum_circuit(v) if isinstance(v, str) else v)
            for k, v in circuits.items()
        }
    elif isinstance(circuits, Iterable):
        circuits = [
            str_to_quantum_circuit(circuit) if isinstance(circuit, str) else circuit
            for circuit in circuits
        ]
    return circuits
