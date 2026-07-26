# This code is part of Qiskit.
#
# (C) Copyright IBM 2026.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Utils for EstimatorV2 unit tests."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from qiskit.primitives.containers.estimator_pub import ObservablesArray

if TYPE_CHECKING:
    from collections.abc import Sequence


@dataclass(frozen=True)
class ParamBasisScenario:
    """A single parameter-basis expansion scenario."""

    parameter_shape: tuple[int, ...]
    """The shape of the array of parameter values."""

    observables_shape: tuple[int, ...]
    """The shape of the observables array."""

    expected_pairs: Sequence[tuple[tuple[int, ...], str]]
    """Expected mapping from each parameter index to the observable(s) assigned after
    broadcasting the parameter and basis dimensions."""


@dataclass(frozen=True)
class ParamBasisScenarios:
    """A collection of scenarios to test parameter-basis expansion."""

    observables: ObservablesArray
    """The observables array used in these scenarios."""

    scenarios: Sequence[ParamBasisScenario]
    """A collection of scenarios."""


PARAM_BASIS_3Q_SCENARIOS = ParamBasisScenarios(
    observables=ObservablesArray(["Z0Z", "X+-", "lrY", "IrI"]),
    scenarios=[
        ParamBasisScenario(
            parameter_shape=(2, 2),
            observables_shape=(2, 2),
            expected_pairs=[((0, 0), "ZZZ"), ((0, 1), "XXX"), ((1, 0), "YYY"), ((1, 1), "IYI")],
        ),
        ParamBasisScenario(
            parameter_shape=(2, 2),
            observables_shape=(2, 2, 1),
            expected_pairs=[
                ((0, 0), "ZZZ"),
                ((0, 0), "YYY"),
                ((0, 1), "ZZZ"),
                ((0, 1), "YYY"),
                ((1, 0), "XXX"),
                ((1, 0), "IYI"),
                ((1, 1), "XXX"),
                ((1, 1), "IYI"),
            ],
        ),
        ParamBasisScenario(
            parameter_shape=(2, 2, 1),
            observables_shape=(2, 2),
            expected_pairs=[
                ((0, 0, 0), "ZZZ"),
                ((0, 0, 0), "XXX"),
                ((0, 1, 0), "YYY"),
                ((1, 0, 0), "ZZZ"),
                ((1, 0, 0), "XXX"),
                ((1, 1, 0), "YYY"),
            ],
        ),
        ParamBasisScenario(
            parameter_shape=(),
            observables_shape=(2, 2),
            expected_pairs=[((), "ZZZ"), ((), "XXX"), ((), "YYY")],
        ),
    ],
)
"""Scenarios to test parameter-basis expansion with three-qubit observables."""
