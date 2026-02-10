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

# pylint: disable=inconsistent-return-statements

"""Noise learner program."""

from __future__ import annotations


from qiskit.circuit import BoxOp
from qiskit.exceptions import QiskitError
from qiskit.quantum_info import Clifford
from samplomatic.utils import undress_box

from qiskit_ibm_runtime.exceptions import IBMInputValueError

from .learning_protocol import LearningProtocol


def find_learning_protocol(instruction: BoxOp) -> LearningProtocol | None:
    """Find which of the supported learning protocols is suitable to learn the noise of ``instruction``.

    Args:
        instruction: The instruction to learn the noise of.

    Returns:
        The supported protocol that can learn the noise of this instruction, or ``None`` if none of the
        protocols are suitable.

    Raises:
        IBMInputValueError: If ``instruction`` does not contain a box.
    """
    if (name := instruction.operation.name) != "box":
        raise IBMInputValueError(f"Expected a 'box' but found '{name}'.")

    undressed_box = undress_box(instruction.operation)

    if len(undressed_box.body) == 0:
        return LearningProtocol.PAULI_LINDBLAD

    # Check if the undressed box contains a layer
    active_qubits = [
        qubit for op in undressed_box.body for qubit in op.qubits if op.name != "barrier"
    ]
    is_layer = len(active_qubits) == len(set(active_qubits))

    # Check if the undressed box only contains two-qubit Clifford gates
    has_only_2q_clifford_gates = all(
        (op.is_standard_gate() and op.operation.num_qubits == 2) or op.name == "barrier"
        for op in undressed_box.body
    )
    if has_only_2q_clifford_gates:
        try:
            Clifford(undressed_box.body)
        except QiskitError:
            has_only_2q_clifford_gates = False

    # Check if the undressed box only contains measurements
    has_only_meas = all(op.name in ["measure", "barrier"] for op in undressed_box.body)

    if is_layer and has_only_2q_clifford_gates:
        return LearningProtocol.PAULI_LINDBLAD

    if is_layer and has_only_meas and len(instruction.qubits) == len(active_qubits):
        return LearningProtocol.TREX

    return None
