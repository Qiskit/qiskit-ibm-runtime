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

from qiskit.primitives.containers import ObservablesArray

if TYPE_CHECKING:
    from collections.abc import Sequence


@dataclass(frozen=True)
class BasisCase:
    """A single parameter-basis expansion test case."""

    parameter_shape: tuple[int, ...]
    """The shape of the array of parameter values."""

    observables_shape: tuple[int, ...]
    """The shape of the observables array."""

    expected_pairs: Sequence[tuple[tuple[int, ...], str]]
    """Expected mapping from each parameter index to the observable(s) assigned after
    broadcasting the parameter and basis dimensions."""


@dataclass(frozen=True)
class ParamBasisTestCases:
    """Test cases for parameter-basis expansion."""

    observables: ObservablesArray
    """The observables array used in the test case."""

    cases: Sequence[BasisCase]
    """A collection of test cases."""


PARAM_BASIS_CASES_3Q = ParamBasisTestCases(
    observables=ObservablesArray(["Z0Z", "X+-", "lrY", "IrI"]),
    cases=[
        BasisCase(
            (2, 2),
            (2, 2),
            [((0, 0), "ZZZ"), ((0, 1), "XXX"), ((1, 0), "YYY"), ((1, 1), "IYI")],
        ),
        BasisCase(
            (2, 2),
            (2, 2, 1),
            [
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
        BasisCase(
            (2, 2, 1),
            (2, 2),
            [
                ((0, 0, 0), "ZZZ"),
                ((0, 0, 0), "XXX"),
                ((0, 1, 0), "YYY"),
                ((1, 0, 0), "ZZZ"),
                ((1, 0, 0), "XXX"),
                ((1, 1, 0), "YYY"),
            ],
        ),
        BasisCase((), (2, 2), [((), "ZZZ"), ((), "XXX"), ((), "YYY")]),
    ],
)
"""Test cases for parameter-basis expansion with three-qubit observables."""
