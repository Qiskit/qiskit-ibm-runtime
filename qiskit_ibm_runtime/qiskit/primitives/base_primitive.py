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
# type: ignore

"""Primitive abstract base class."""

from __future__ import annotations
from typing import Optional

from abc import ABC, abstractmethod
from dataclasses import replace
from collections.abc import Sequence

import numpy as np

from qiskit.circuit import QuantumCircuit

from .options import BasePrimitiveOptions, BasePrimitiveOptionsLike


class BasePrimitiveV2(ABC):
    """Primitive abstract base class."""

    version = 2
    _options_class: type[BasePrimitiveOptions] = BasePrimitiveOptions

    def __init__(self, options: Optional[BasePrimitiveOptionsLike] = None):
        self._options: type(self)._options_class
        self._set_options(options)

    @property
    def options(self) -> BasePrimitiveOptions:
        """Options for BaseEstimator"""
        return self._options

    @options.setter
    def options(self, options: BasePrimitiveOptionsLike) -> None:
        self._set_options(options)

    def _set_options(self, options):
        if options is None:
            self._options = self._options_class()
        elif isinstance(options, dict):
            self._options = self._options_class(**options)
        elif isinstance(options, self._options_class):
            self._options = options
        else:
            raise TypeError(
                f"Invalid 'options' type. It can only be a dictionary of {self._options_class}"
            )

#     @abstractmethod
#     def set_options(self, **fields) -> None:
#         """Set options values for the estimator.

#         Args:
#             **fields: The fields to update the options
#         """
#         raise NotImplementedError()

#     @staticmethod
#     def _validate_circuits(
#         circuits: Sequence[QuantumCircuit] | QuantumCircuit,
#     ) -> tuple[QuantumCircuit, ...]:
#         if isinstance(circuits, QuantumCircuit):
#             circuits = (circuits,)
#         elif not isinstance(circuits, Sequence) or not all(
#             isinstance(cir, QuantumCircuit) for cir in circuits
#         ):
#             raise TypeError("Invalid circuits, expected Sequence[QuantumCircuit].")
#         elif not isinstance(circuits, tuple):
#             circuits = tuple(circuits)
#         if len(circuits) == 0:
#             raise ValueError("No circuits were provided.")
#         return circuits

#     @staticmethod
#     def _validate_parameter_values(
#         parameter_values: Sequence[Sequence[float]] | Sequence[float] | float | None,
#         default: Sequence[Sequence[float]] | Sequence[float] | None = None,
#     ) -> tuple[tuple[float, ...], ...]:
#         # Allow optional (if default)
#         if parameter_values is None:
#             if default is None:
#                 raise ValueError("No default `parameter_values`, optional input disallowed.")
#             parameter_values = default

#         # Support numpy ndarray
#         if isinstance(parameter_values, np.ndarray):
#             parameter_values = parameter_values.tolist()
#         elif isinstance(parameter_values, Sequence):
#             parameter_values = tuple(
#                 vector.tolist() if isinstance(vector, np.ndarray) else vector
#                 for vector in parameter_values
#             )

#         # Allow single value
#         if _isreal(parameter_values):
#             parameter_values = ((parameter_values,),)
#         elif isinstance(parameter_values, Sequence) and not any(
#             isinstance(vector, Sequence) for vector in parameter_values
#         ):
#             parameter_values = (parameter_values,)

#         # Validation
#         if (
#             not isinstance(parameter_values, Sequence)
#             or not all(isinstance(vector, Sequence) for vector in parameter_values)
#             or not all(all(_isreal(value) for value in vector) for vector in parameter_values)
#         ):
#             raise TypeError("Invalid parameter values, expected Sequence[Sequence[float]].")

#         return tuple(tuple(float(value) for value in vector) for vector in parameter_values)

#     @staticmethod
#     def _cross_validate_circuits_parameter_values(
#         circuits: tuple[QuantumCircuit, ...], parameter_values: tuple[tuple[float, ...], ...]
#     ) -> None:
#         if len(circuits) != len(parameter_values):
#             raise ValueError(
#                 f"The number of circuits ({len(circuits)}) does not match "
#                 f"the number of parameter value sets ({len(parameter_values)})."
#             )
#         for i, (circuit, vector) in enumerate(zip(circuits, parameter_values)):
#             if len(vector) != circuit.num_parameters:
#                 raise ValueError(
#                     f"The number of values ({len(vector)}) does not match "
#                     f"the number of parameters ({circuit.num_parameters}) for the {i}-th circuit."
#                 )


# def _isint(obj: Sequence[Sequence[float]] | Sequence[float] | float) -> bool:
#     """Check if object is int."""
#     int_types = (int, np.integer)
#     return isinstance(obj, int_types) and not isinstance(obj, bool)


# def _isreal(obj: Sequence[Sequence[float]] | Sequence[float] | float) -> bool:
#     """Check if object is a real number: int or float except ``±Inf`` and ``NaN``."""
#     float_types = (float, np.floating)
#     return _isint(obj) or isinstance(obj, float_types) and float("-Inf") < obj < float("Inf")
