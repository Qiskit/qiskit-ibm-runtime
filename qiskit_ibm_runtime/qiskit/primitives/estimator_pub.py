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
# type: ignore

"""
Estiamtor Pub class
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Union, Tuple

import numpy as np

from qiskit import QuantumCircuit

from .base_pub import BasePub
from .bindings_array import BindingsArray, BindingsArrayLike
from .observables_array import ObservablesArray, ObservablesArrayLike
from .shape import ShapedMixin


@dataclass(frozen=True)
class EstimatorPub(BasePub, ShapedMixin):
    """Pub for Estimator.
    Pub is composed of triple (circuit, observables, parameter_values).
    """

    observables: ObservablesArray
    parameter_values: BindingsArray = BindingsArray([], shape=())
    _shape: tuple[int, ...] = field(init=False)

    def __post_init__(self):
        shape = np.broadcast_shapes(self.observables.shape, self.parameter_values.shape)
        super().__setattr__("_shape", shape)

    @classmethod
    def coerce(cls, pub: EstimatorPubLike) -> EstimatorPub:
        """Coerce EstimatorPubLike into EstimatorPub.

        Args:
            pub: an object to be estimator pub.

        Returns:
            A coerced estiamtor pub.

        Raises:
            ValueError: If input values are invalid.
        """
        if isinstance(pub, EstimatorPub):
            return pub
        if len(pub) != 2 and len(pub) != 3:
            raise ValueError(f"The length of pub must be 2 or 3, but length {len(pub)} is given.")
        circuit = pub[0]
        observables = ObservablesArray.coerce(pub[1])
        parameter_values = (
            BindingsArray.coerce(pub[2]) if len(pub) == 3 else BindingsArray([], shape=(1,))
        )
        return cls(circuit=circuit, observables=observables, parameter_values=parameter_values)

    def validate(self) -> None:
        """Validate the pub."""
        super().validate()
        self.observables.validate()
        self.parameter_values.validate()
        # Cross validate circuits and observables
        # for i, observable in enumerate(self.observables):
        #     num_qubits = len(next(iter(observable)))

        num_qubits = len(next(iter(self.observables.ravel()[0].keys())))
        if self.circuit.num_qubits != num_qubits:
            raise ValueError(
                f"The number of qubits of the circuit ({self.circuit.num_qubits}) does "
                f"not match the number of qubits of the observable ({num_qubits})."
            )
        # Cross validate circuits and paramter_values
        num_parameters = self.parameter_values.num_parameters
        if num_parameters != self.circuit.num_parameters:
            raise ValueError(
                f"The number of values ({num_parameters}) does not match "
                f"the number of parameters ({self.circuit.num_parameters}) for the circuit."
            )


EstimatorPubLike = Union[
    EstimatorPub, Tuple[QuantumCircuit, ObservablesArrayLike, BindingsArrayLike]
]
