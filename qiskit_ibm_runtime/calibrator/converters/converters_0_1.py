# This code is part of Qiskit.
#
# (C) Copyright IBM 2025-2026.
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

from ibm_quantum_schemas.calibrator.version_0_1 import OptionsModel, ParamsModel

from ...options_models.calibrator import CalibratorOptions


def calibrator_program_from_0_1(model: ParamsModel) -> CalibratorOptions:
    """Convert a V0.1 model to the inputs of a calibrator program."""
    options = CalibratorOptions()
    options.experimental = model.options.experimental
    return options


def calibrator_program_to_0_1(options: CalibratorOptions) -> ParamsModel:
    """Convert the inputs of a calibrator program to a V0.1 model."""
    return ParamsModel(options=OptionsModel(experimental=options.experimental))
