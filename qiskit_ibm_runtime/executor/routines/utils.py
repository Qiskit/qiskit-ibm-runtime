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


def extract_shots_from_pubs(pubs: list[SamplerPub], default_shots: int | None = None) -> int:
    """Extract and validate shots value from a list of SamplerPub objects.

    This function determines the shots value by examining all pubs and ensures
    that all pubs have the same number of shots. If a pub doesn't specify shots,
    the default_shots value is used.

    Args:
        pubs: List of sampler pubs to extract shots from.
        default_shots: Default number of shots if not specified in pubs.

    Returns:
        The validated shots value that all pubs share.

    Raises:
        IBMInputValueError: If pubs list is empty, if shots are not specified
            anywhere, or if pubs have different shot values.
    """
    if not pubs:
        raise IBMInputValueError("At least one pub must be provided.")

    pub_shots = {pub.shots or default_shots for pub in pubs}
    if None in pub_shots:
        raise IBMInputValueError("Shots must be specified either in the pub or as default_shots.")
    pub_shots = {s for s in pub_shots if s is not None}  # For mypy typing
    if len(pub_shots) != 1:
        raise IBMInputValueError(f"All pubs must have the same number of shots. Found: {pub_shots}")
    return next(iter(pub_shots))
