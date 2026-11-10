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

"""Tests the converters for calibrator jobs."""

import datetime

from ibm_quantum_schemas.calibrator.version_0_1 import CalibratorResultModel

from qiskit_ibm_runtime.calibrator.converters import (
    calibrator_program_from_0_1,
    calibrator_program_to_0_1,
)
from qiskit_ibm_runtime.decoders.calibrator.converters import calibrator_result_from_0_1
from qiskit_ibm_runtime.options_models.calibrator import CalibratorOptions


class TestCalibratorConverters:
    """Tests the converters for calibrator jobs."""

    def test_calibrator_program_to_from__0_1(self) -> None:
        """Test the function ``calibrator_program_to/from_0_1``."""
        options = CalibratorOptions()
        params_model = calibrator_program_to_0_1(options)

        assert params_model.schema_version == "v0.1"
        assert isinstance(params_model.options.experimental, dict)

        new_options = calibrator_program_from_0_1(params_model)
        assert new_options == options

    def test_calibrator_result_from_0_1(self) -> None:
        """Test the function ``calibrator_result_from_0_1``."""
        start = datetime.datetime.now()
        stop = start + datetime.timedelta(seconds=10)
        result_model = CalibratorResultModel(start=start, stop=stop)
        result = calibrator_result_from_0_1(result_model)
        assert result.start == start
        assert result.stop == stop
