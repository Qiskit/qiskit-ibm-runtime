# This code is part of Qiskit.
#
# (C) Copyright IBM 2022.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Execution options."""

from typing import Literal, get_args
from pydantic import Field, ConfigDict
from pydantic.functional_validators import model_validator, field_validator
from pydantic.dataclasses import dataclass as pydantic_dataclass

ExecutionSupportedOptions = Literal[
    "shots",
    "init_qubits",
]


@pydantic_dataclass
class ExecutionOptions:
    """Execution options.

    Args:
        shots: Number of repetitions of each circuit, for sampling. Default: 4000.

        init_qubits: Whether to reset the qubits to the ground state for each shot.
            Default: ``True``.
    """

    shots: int = 4000
    init_qubits: bool = True


    # @model_validator(mode="after")
    # def _validate_model(
    #         self,
    # ):
    #     """Validate that execution options are legal.
    #     Raises:
    #         ValueError: if any execution option is not supported
    #     """
    #     for opt in execution_options:
    #         if not opt in get_args(ExecutionSupportedOptions):
    #             raise ValueError(f"Unsupported value '{opt}' for execution.")
