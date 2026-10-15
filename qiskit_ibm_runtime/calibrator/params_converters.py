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

"""Converters for quantum program params."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Generic, TypeVar

from ibm_quantum_schemas.calibrator.version_0_1 import ParamsModel as ParamsModel_0_1

from .converters import calibrator_program_from_0_1, calibrator_program_to_0_1

if TYPE_CHECKING:
    from collections.abc import Callable

    from ibm_quantum_schemas.common import BaseParamsModel

    from ..options_models.calibrator import CalibratorOptions


ModelT = TypeVar("ModelT", bound="BaseParamsModel")


@dataclass(frozen=True)
class ParamsConverter(Generic[ModelT]):
    """A helper to store params models and converters."""

    model: type[ModelT]
    """The model describing the inputs of a calibrator job, or 'params'."""

    decoder: Callable[[ModelT], CalibratorOptions]
    """A function to decode the inputs of a calibrator job."""

    encoder: Callable[
        [
            CalibratorOptions,
        ],
        ModelT,
    ]
    """A function to encode the inputs of a calibrator job."""


CALIBRATOR_PARAMS_CONVERTERS = {
    "v0.1": ParamsConverter(
        ParamsModel_0_1, calibrator_program_from_0_1, calibrator_program_to_0_1
    ),
}
"""Converter to/from schema model for the inputs of calibrator jobs."""
