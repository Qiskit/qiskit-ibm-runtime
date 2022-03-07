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

        result = session(circuits, observables, parameters)

    where the i-th elements of `result` correspond to the expectation using the circuit and
    observable given by `circuits[i]`, `observables[i]`, and the parameters bounds by `parameters[i]`.

    Args:
        values (np.ndarray): the array of the expectation values.
        metadata (list[dict]): list of the metadata.
    """

    values: "np.ndarray[Any, np.dtype[np.float64]]"
    metadata: list[dict[str, Any]]
    shots: int


class EstimatorSession(RuntimeSession):
    """Estimator session"""

    def __call__(
        self,
        circuits: Sequence[int],
        observables: Sequence[int],
        parameters: Sequence[Sequence[float]],
        **run_options: Any,
    ) -> EstimatorResult:
        """Estimates expectation values for given inputs in a runtime session.

        Args:
            circuits: A list of circuit indices.
            observables: A list of observable indices.
            parameters: Concrete parameters to be bound.
            **run_options: A collection of kwargs passed to backend.run().

        Returns:
            An instance of EstimatorResult.
        """
        self.write(
            circuits_indices=circuits,
            observables_indices=observables,
            parameters_values=parameters,
            run_options=run_options,
        )
        raw_result = self.read()
        return EstimatorResult(
            values=raw_result["values"],
            metadata=raw_result["metadata"],
            shots=raw_result["shots"],
        )
