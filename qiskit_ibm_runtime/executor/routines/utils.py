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

"""Utility functions for executor-based SamplerV2."""

from __future__ import annotations

from qiskit.circuit import BoxOp, QuantumCircuit
from qiskit.primitives.containers.sampler_pub import SamplerPub

from ...exceptions import IBMInputValueError
from ...quantum_program import QuantumProgram
from ...quantum_program.quantum_program import CircuitItem


def validate_no_boxes(circuit: QuantumCircuit) -> None:
    """Validate that a circuit contains no BoxOp instructions.

    Args:
        circuit: The circuit to validate.

    Raises:
        IBMInputValueError: If the circuit contains BoxOp instructions.
    """
    for instruction in circuit.data:
        if isinstance(instruction.operation, BoxOp):
            raise IBMInputValueError(
                f"Circuit contains a BoxOp instruction '{instruction.operation.name}' "
                "which is not supported in this minimal implementation. "
                "BoxOp support (for twirling) will be added in a future phase."
            )


def pubs_to_quantum_program(
    pubs: list[SamplerPub], default_shots: int | None = None
) -> QuantumProgram:
    """Convert a list of SamplerPub objects to a QuantumProgram.

    Args:
        pubs: List of sampler pubs to convert.
        default_shots: Default number of shots if not specified in pubs.

    Returns:
        A QuantumProgram containing CircuitItem objects for each pub.

    Raises:
        IBMInputValueError: If circuits contain boxes or if shots are not specified.
    """
    if not pubs:
        raise IBMInputValueError("At least one pub must be provided.")

    # Determine shots - all pubs should have the same shots value
    shots = None
    for pub in pubs:
        pub_shots = pub.shots if pub.shots is not None else default_shots
        if pub_shots is None:
            raise IBMInputValueError(
                "Shots must be specified either in the pub or as default_shots."
            )
        if shots is None:
            shots = pub_shots
        elif shots != pub_shots:
            raise IBMInputValueError(
                f"All pubs must have the same number of shots. Found {shots} and {pub_shots}."
            )

    # Validate circuits don't contain boxes
    for pub in pubs:
        validate_no_boxes(pub.circuit)

    # Create QuantumProgram with CircuitItem for each pub
    items = []
    for pub in pubs:
        # Convert parameter values to numpy array
        if pub.parameter_values.num_parameters > 0:
            # Get the parameter values as a numpy array
            param_values = pub.parameter_values.as_array()
        else:
            param_values = None

        items.append(
            CircuitItem(
                circuit=pub.circuit,
                circuit_arguments=param_values,
            )
        )

    return QuantumProgram(shots=shots, items=items)
