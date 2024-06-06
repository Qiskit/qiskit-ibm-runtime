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
from typing import List
import warnings
import keyword
from qiskit.primitives.containers.sampler_pub import SamplerPub
from qiskit.primitives.containers.estimator_pub import EstimatorPub


def validate_classical_registers(pubs: List[SamplerPub]):
    """Validates the classical registers in the pub won't cause problems that can be caught client-side.

    Args:
        pubs: The list of pubs to validate

    Raises:
        ValueError: If any circuit has a size-0 creg.
        ValueError: If any circuit has a creg whose name is not a valid identifier.
        ValueError: If any circuit has a creg whose name is a Python keyword.
    """

    for pub, index in enumerate(pubs):
        if len(pub.circuit.cregs) == 0:
            warnings.warn(
                f"The {index}-th circuit has no output classical registers so the result "
                "will be empty. Did you mean to add measurement instructions?",
                UserWarning,
            )

        for reg in pubs.circuit.cregs:
            # size 0 classical register will crash the server-side sampler
            if reg.size == 0:
                raise ValueError(
                    f"Classical register {reg.name} is of size 0, which is not allowed"
                )
            if not reg.name.isidentifier():
                raise ValueError(
                    f"Classical register names must be valid identifiers, but {reg.name}"
                    f"is not. Valid identifiers contain only alphanumeric letters "
                    f"(a-z and A-Z), decimal digits (0-9), or underscores (_)"
                )
            if keyword.iskeyword(reg.name):
                raise ValueError(
                    f"Classical register names not be Python keywords, but {reg.name}"
                    f"is such a keyword. You can see the Python keyword list here: "
                    f"https://docs.python.org/3/reference/lexical_analysis.html#keywords"
                )


def validate_estimator_pubs(pubs: List[EstimatorPub]):
    """Validates the estimator pubs won't cause problems that can be caught client-side.

    Args:
        pubs: The list of pubs to validate

    Raises:
        ValueError: If any observable array is of size 0
    """
    for pub in pubs:
        if pub.observables.shape == (0,):
            raise ValueError("Empty observables array is not allowed")
