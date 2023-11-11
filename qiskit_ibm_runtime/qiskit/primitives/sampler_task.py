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

"""
Sampler Task class
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Union, Optional

import numpy as np

from qiskit import QuantumCircuit

from .base_task import BaseTask
from .bindings_array import BindingsArray, BindingsArrayLike
from .shape import ShapedMixin


@dataclass(frozen=True)
class SamplerTask(BaseTask, ShapedMixin):
    """Task for Sampler.
    Task is composed of triple (circuit, parameter_values).
    """

    parameter_values: Optional[BindingsArray] = BindingsArray([], shape=())
    _shape: tuple[int, ...] = field(init=False)

    def __post_init__(self):
        super().__setattr__("_shape", self.parameter_values.shape)

    @classmethod
    def coerce(cls, task: SamplerTaskLike) -> SamplerTask:
        """Coerce SamplerTaskLike into SamplerTask.

        Args:
            task: an object to be sampler task.

        Returns:
            A coerced estiamtor task.
        """
        if isinstance(task, SamplerTask):
            return task
        if len(task) != 1 and len(task) != 2:
            raise ValueError(f"The length of task must be 1 or 2, but length {len(task)} is given.")
        circuit = task[0]
        parameter_values = (
            BindingsArray.coerce(task[1]) if len(task) == 2 else BindingsArray([], shape=())
        )
        return cls(circuit=circuit, parameter_values=parameter_values)

    def validate(self) -> None:
        """Validate the task."""
        super().validate()
        self.parameter_values.validate()
        # Cross validate circuits and paramter_values
        num_parameters = self.parameter_values.num_parameters
        if num_parameters != self.circuit.num_parameters:
            raise ValueError(
                f"The number of values ({num_parameters}) does not match "
                f"the number of parameters ({self.circuit.num_parameters}) for the circuit."
            )


SamplerTaskLike = Union[
    SamplerTask, tuple[QuantumCircuit, BindingsArrayLike]
]
