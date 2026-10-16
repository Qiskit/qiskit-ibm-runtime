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

"""Transport conversion functions."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ...results import CalibratorResult

if TYPE_CHECKING:
    from ibm_quantum_schemas.calibrator.version_0_1 import (
        CalibratorResultModel as CalibratorResultModel_0_1,
    )


def calibrator_result_from_0_1(model: CalibratorResultModel_0_1) -> CalibratorResult:
    """Convert a V0.1 model to a :class:`QuantumProgramResult`."""
    return CalibratorResult(start=model.start, stop=model.stop)
