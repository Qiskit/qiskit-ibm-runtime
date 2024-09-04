# This code is part of Qiskit.
#
# (C) Copyright IBM 2024.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Utilities for data validation."""
from typing import List, Sequence, Optional, Any
import warnings
import keyword

from qiskit import QuantumCircuit
from qiskit.transpiler import Target
from qiskit.primitives.containers.sampler_pub import SamplerPub
from qiskit.primitives.containers.estimator_pub import EstimatorPub
from qiskit_ibm_runtime.utils.utils import is_isa_circuit, are_circuits_dynamic
from qiskit_ibm_runtime.exceptions import IBMInputValueError


def validate_classical_registers(pubs: List[SamplerPub]) -> None:
    """Validates the classical registers in the pub won't cause problems that can be caught client-side.

    Args:
        pubs: The list of pubs to validate

    Raises:
        ValueError: If any circuit has a size-0 creg.
        ValueError: If any circuit has a creg whose name is not a valid identifier.
        ValueError: If any circuit has a creg whose name is a Python keyword.
    """

    for index, pub in enumerate(pubs):
        if len(pub.circuit.cregs) == 0:
            warnings.warn(
                f"The {index}-th circuit has no output classical registers so the result "
                "will be empty. Did you mean to add measurement instructions?",
                UserWarning,
            )

        for reg in pub.circuit.cregs:
            # size 0 classical register will crash the server-side sampler
            if reg.size == 0:
                raise ValueError(
                    f"Classical register {reg.name} is of size 0, which is not allowed"
                )
            if not reg.name.isidentifier():
                raise ValueError(
                    f"Classical register names must be valid identifiers, but {reg.name} "
                    f"is not. Valid identifiers contain only alphanumeric letters "
                    f"(a-z and A-Z), decimal digits (0-9), or underscores (_)"
                )
            if keyword.iskeyword(reg.name):
                raise ValueError(
                    f"Classical register names cannot be Python keywords, but {reg.name} "
                    f"is such a keyword. You can see the Python keyword list here: "
                    f"https://docs.python.org/3/reference/lexical_analysis.html#keywords"
                )


def validate_estimator_pubs(pubs: List[EstimatorPub]) -> None:
    """Validates the estimator pubs won't cause problems that can be caught client-side.

    Args:
        pubs: The list of pubs to validate

    Raises:
        ValueError: If any observable array is of size 0
    """
    for pub in pubs:
        if pub.observables.shape == (0,):
            raise ValueError("Empty observables array is not allowed")


def validate_isa_circuits(circuits: Sequence[QuantumCircuit], target: Target) -> None:
    """Validate if all circuits are ISA circuits

    Args:
        circuits: A list of QuantumCircuits.
        target: The backend target
    """
    for circuit in circuits:
        message = is_isa_circuit(circuit, target)
        if message:
            raise IBMInputValueError(
                message
                + " Circuits that do not match the target hardware definition are no longer "
                "supported after March 4, 2024. See the transpilation documentation "
                "(https://docs.quantum.ibm.com/guides/transpile) for instructions "
                "to transform circuits and the primitive examples "
                "(https://docs.quantum.ibm.com/guides/primitives-examples) to see "
                "this coupled with operator transformations."
            )


def validate_no_dd_with_dynamic_circuits(circuits: List[QuantumCircuit], options: Any) -> None:
    """Validate that if dynamical decoupling options are enabled,
    no circuit in the pubs is dynamic

    Args:
        circuits: A list of QuantumCircuits.
        options: The runtime options
    """
    if not hasattr(options, "dynamical_decoupling") or not options.dynamical_decoupling.enable:
        return
    if are_circuits_dynamic(circuits, False):
        raise IBMInputValueError(
            "Dynamical decoupling currently cannot be used with dynamic circuits"
        )


def validate_job_tags(job_tags: Optional[List[str]]) -> None:
    """Validates input job tags.

    Args:
        job_tags: Job tags to be validated.

    Raises:
        IBMInputValueError: If the job tags are invalid.
    """
    if job_tags and (
        not isinstance(job_tags, list) or not all(isinstance(tag, str) for tag in job_tags)
    ):
        raise IBMInputValueError("job_tags needs to be a list of strings.")
