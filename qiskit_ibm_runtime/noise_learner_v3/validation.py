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

"""Noise learner program."""

from __future__ import annotations

import numpy as np
from qiskit.circuit import (
    CircuitInstruction,
    ControlFlowOp,
    ParameterExpression,
    QuantumRegister,
    BoxOp,
)
from qiskit.transpiler import Target
from samplomatic.annotations import Twirl
from samplomatic.utils import get_annotation

from .find_learning_protocol import find_learning_protocol
from ..models.backend_configuration import BackendConfiguration

from ..exceptions import IBMInputValueError
from ..options import NoiseLearnerV3Options
from ..options.post_selection_options import DEFAULT_X_PULSE_TYPE


def validate_options(options: NoiseLearnerV3Options, configuration: BackendConfiguration) -> None:
    """Validates the options of a noise learner job."""
    if options.post_selection.enable is True:  # type: ignore[union-attr]
        x_pulse_type = (
            options.post_selection.x_pulse_type or DEFAULT_X_PULSE_TYPE  # type: ignore[union-attr]
        )
        if x_pulse_type not in (basis_gates := configuration.basis_gates):
            raise ValueError(
                f"Cannot apply Post Selection with X-pulse type '{x_pulse_type}' on a backend with "
                f"basis gates {basis_gates}."
            )


def validate_instruction(instruction: CircuitInstruction, target: Target) -> None:
    """Validates that an instruction is valid for the noise learner.

    Args:
        instruction: The instruction to validate.
        target: The target to validate against.

    Raises:
        IBMInputValueError: If ``instruction`` does not contain a box.
        IBMInputValueError: If the box in ``instruction`` does not contain a ``Twirl`` annotation.
        IBMInputValueError: If ``instruction`` contains unphysical qubits.
        IBMInputValueError: If the box in ``instruction`` contains non-ISA gates.
        IBMInputValueError: If ``instruction`` cannot be learned by any of the supported learning
            protocols.
    """
    if reason := _contains_twirled_box(instruction):
        raise IBMInputValueError(reason)

    if reason := _contains_physical_qubits(instruction, target):
        raise IBMInputValueError(reason)

    if reason := _is_isa_instruction(instruction, target):
        raise IBMInputValueError(reason)

    if not find_learning_protocol(instruction):
        raise IBMInputValueError(
            "Found an instruction that cannot be learned by any of the supported "
            "learning protocols."
        )


def _contains_twirled_box(instruction: CircuitInstruction) -> str:
    """Check that an instruction contains a box with a twirl annotation.

    Args:
        instruction: The instruction to validate.

    Returns:
        An error message if ``instruction`` does not contain a twirled-annotated box, or an empty
        string otherwise.
    """
    if (name := instruction.operation.name) != "box":
        return f"Expected a 'box' but found '{name}'."

    if not get_annotation(instruction.operation, Twirl):
        return "Found a box without a ``Twirl`` annotation."

    return ""


def _contains_physical_qubits(instruction: CircuitInstruction, target: Target) -> str:
    """Check that ``instruction`` acts on physical qubits.

    Args:
        instruction: The instruction to validate.
        target: The target to validate against.

    Returns:
        An error message if ``instruction`` doesn't contain physical qubits, an empty string otherwise.
    """
    qreg = QuantumRegister(target.num_qubits, "q")
    if unphysical_qubits := [qubit for qubit in instruction.qubits if qubit not in qreg]:
        return (
            f"Every qubit must be part of {qreg}, but the following qubits "
            f"are not part of it: {unphysical_qubits}."
        )
    return ""


def _is_isa_instruction(instruction: CircuitInstruction, target: Target) -> str:
    """Check that a box instruction contains an ISA circuit.

    Assumes but does not check that:
        * ``instruction`` contains a box.
        * ``instruction`` contains physical qubits.

    Args:
        instruction: The instruction to validate.
        target: The target to validate against.

    Returns:
        An error message if ``instruction`` is not ISA, or an empty string otherwise.
    """
    if instruction.operation.num_qubits > target.num_qubits:
        return (
            f"The instruction has {instruction.num_qubits} qubits "
            f"but the target system requires {target.num_qubits} qubits."
        )

    # A map from the instruction qubits to indexes
    qreg = QuantumRegister(target.num_qubits, "q")
    qubit_map = {qubit: idx for idx, qubit in enumerate(qreg)}

    # A map from the box qubits to indexes
    box_qubit_map = {
        box_qubit: qubit_map[instruction_qubit]
        for instruction_qubit, box_qubit in zip(
            instruction.qubits, instruction.operation.body.qubits
        )
    }

    for op in instruction.operation.body:
        if (
            not target.instruction_supported(
                name := op.name,
                qargs := tuple(box_qubit_map[box_qubit] for box_qubit in op.qubits),
            )
            and op.name != "barrier"
        ):
            return f"The instruction {op.name} on qubits {qargs} is not supported by the target system."

        # rzz gate is calibrated only for the range [0, pi/2].
        # We allow an angle value of a bit more than pi/2, to compensate floating point rounding
        # errors (beyond pi/2 does not trigger an error down the stack, only may become less
        # accurate).
        if name == "rzz" and (reason := _validate_rzz_angle(op.params[0])):
            return reason

        if isinstance(op, (ControlFlowOp, BoxOp)):
            return f"The instruction {op.name} on qubits {qargs} is not supported by the noise learner."

    return ""


def _validate_rzz_angle(angle: float) -> str:
    """Verify that all rzz angles are in the range ``[0, pi/2]``.

    We allow an angle value of a bit more than pi/2, to compensate floating point rounding
    errors.

    Args:
        angle: An angle to be checked

    Returns:
        An empty string if the angle is valid, otherwise an error message.
    """
    if not isinstance(angle, ParameterExpression) and (angle < 0.0 or angle > np.pi / 2 + 1e-10):
        return (
            f"'rzz' is supported only for angles in the range ``[0, pi/2]``, but an angle "
            f"({angle}) outside of this range has been requested."
        )
    return ""
