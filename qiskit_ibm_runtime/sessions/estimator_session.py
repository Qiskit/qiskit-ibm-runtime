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

from typing import List, Optional, Union, Tuple, Any

# TODO remove when importing EstimatorResult from terra
from dataclasses import dataclass
import numpy as np

# TODO uncomment when importing EstimatorResult and Group from terra
# from qiskit.primitives import EstimatorResult
# from qiskit.primitives.base_estimator import Group

from .runtime_session import RuntimeSession

# TODO remove and import Group from terra
@dataclass(frozen=True)
class Group:
    """The dataclass represents indices of circuit and observable."""

    circuit_index: int
    observable_index: int


# TODO remove and import from terra
@dataclass(frozen=True)
class EstimatorResult:
    """
    Result of ExpectationValue
    #TODO doc
    """

    values: "np.ndarray[Any, np.dtype[np.float64]]"
    variances: "np.ndarray[Any, np.dtype[np.float64]]"
    shots: int
    # standard_errors: np.ndarray[Any, np.dtype[np.float64]]
    # metadata: list[dict[str, Any]]

    def __add__(self, other: EstimatorResult) -> EstimatorResult:
        values = np.concatenate([self.values, other.values])
        variances = np.concatenate([self.variances, other.variances])
        shots = self.shots + other.shots
        return EstimatorResult(values, variances, shots)


class EstimatorSession(RuntimeSession):
    """Estimator session"""

    def __call__(
        self,
        parameters: List[List[float]] = None,
        grouping: Optional[List[Union[Group, Tuple[int, int]]]] = None,
        **run_options: Any,
    ) -> EstimatorResult:
        self.write(parameters=parameters, grouping=grouping, run_options=run_options)
        raw_result = self.read()
        return EstimatorResult(
            values=raw_result["values"],
            variances=raw_result["variances"],
            shots=raw_result["shots"],
        )
