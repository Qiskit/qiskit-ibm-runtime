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

"""Sampler session"""

# TODO remove when importing SamplerResult from terra
from __future__ import annotations

from typing import Optional, List, Any, Sequence

# TODO remove when importing SamplerResult from terra
from dataclasses import dataclass

# TODO remove when importing SamplerResult from terra
from qiskit.result import QuasiDistribution

# TODO uncomment when importing from terra
# from qiskit.primitives import SamplerResult

from .runtime_session import RuntimeSession

# TODO use SamplerResult from terra once released
@dataclass(frozen=True)
class SamplerResult:
    """
    Result of Sampler

    Example::

        result = sampler(circuit_indices, parameter_values)

    where the i-th elements of `result` correspond to the expectation using the circuit
    given by `circuit_indices[i]` and the parameters bounds by `parameter_values[i]`.
    """

    quasi_dists: list[QuasiDistribution]
    metadata: list[dict[str, Any]]


class SamplerSession(RuntimeSession):
    """Sampler session"""

    def __call__(
        self,
        circuit_indices: Sequence[int],
        parameter_values: Sequence[Sequence[float]],
        **run_options: Any,
    ) -> SamplerResult:
        """Calculates probabilites or quasi-probabilities for given inputs in a runtime session.

        Args:
            circuit_indices: A list of circuit indices.
            parameter_values: Concrete parameters to be bound.
            **run_options: A collection of kwargs passed to backend.run().

        Returns:
            An instance of SamplerResult.
        """
        self.write(
            circuit_indices=circuit_indices,
            parameter_values=parameter_values,
            run_options=run_options,
        )
        raw_result = self.read()
        return SamplerResult(
            quasi_dists=raw_result["quasi_dists"],
            metadata=raw_result["metadata"],
        )
