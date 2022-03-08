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

"""Estimator session"""

# TODO remove when importing EstimatorResult from terra
from __future__ import annotations

from typing import TYPE_CHECKING, Sequence, List, Optional, Any

# TODO remove when importing EstimatorResult from terra
from dataclasses import dataclass

from .runtime_session import RuntimeSession

# TODO remove when importing EstimatorResult from terra
if TYPE_CHECKING:
    import numpy as np

# TODO uncomment when importing EstimatorResult from terra
# from qiskit.primitives import EstimatorResult

# TODO use EstimatorResult from terra once released
@dataclass(frozen=True)
class EstimatorResult:
    """
    Result of ExpectationValue

    Example::

        result = estimator(circuit_indices, observable_indices, parameter_values)

    where the i-th elements of `result` correspond to the expectation using the circuit and
    observable given by `circuit_indices[i]`, `observable_indices[i]`, and the parameters
    bounds by `parameter_values[i]`.

    Args:
        values (np.ndarray): An array of expectation values.
        metadata (list[dict]): A list of metadata.
    """

    values: "np.ndarray[Any, np.dtype[np.float64]]"
    metadata: list[dict[str, Any]]


class EstimatorSession(RuntimeSession):
    """Estimator session"""

    def __call__(
        self,
        circuit_indices: Sequence[int],
        observable_indices: Sequence[int],
        parameter_values: Sequence[Sequence[float]],
        **run_options: Any,
    ) -> EstimatorResult:
        """Estimates expectation values for given inputs in a runtime session.

        Args:
            circuit_indices: A list of circuit indices.
            observable_indices: A list of observable indices.
            parameter_values: Concrete parameters to be bound.
            **run_options: A collection of kwargs passed to backend.run().

        Returns:
            An instance of EstimatorResult.
        """
        self.write(
            circuit_indices=circuit_indices,
            observable_indices=observable_indices,
            parameter_values=parameter_values,
            run_options=run_options,
        )
        raw_result = self.read()
        return EstimatorResult(
            values=raw_result["values"],
            metadata=raw_result["metadata"],
        )
