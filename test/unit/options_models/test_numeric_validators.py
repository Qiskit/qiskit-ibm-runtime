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

"""Tests restoring the numeric range validators dropped from the wrapper options (DR-VAL)."""

from pydantic import ValidationError

from qiskit_ibm_runtime.options_models.estimator import EstimatorOptions
from qiskit_ibm_runtime.options_models.measure_noise_learning import MeasureNoiseLearningOptions
from qiskit_ibm_runtime.options_models.pec import PecOptions
from qiskit_ibm_runtime.options_models.twirling import TwirlingOptions

from ...ibm_test_case import IBMTestCase


class TestNumericValidators(IBMTestCase):
    """Test that invalid numeric option values raise ``ValidationError``."""

    def test_default_precision_must_be_positive(self):
        """``default_precision <= 0`` should raise, matching legacy ``gt=0``."""
        with self.assertRaisesRegex(ValidationError, "default_precision"):
            EstimatorOptions(default_precision=0)
        with self.assertRaisesRegex(ValidationError, "default_precision"):
            EstimatorOptions(default_precision=-1)
        # Sane value still works.
        EstimatorOptions(default_precision=0.01)

    def test_default_shots_cannot_be_negative(self):
        """``default_shots < 0`` should raise, matching legacy ``ge=0``."""
        with self.assertRaisesRegex(ValidationError, "default_shots"):
            EstimatorOptions(default_shots=-1)
        # Zero and None are both valid.
        EstimatorOptions(default_shots=0)
        EstimatorOptions(default_shots=None)

    def test_twirling_num_randomizations_must_be_positive(self):
        """``twirling.num_randomizations = 0`` should raise, matching legacy ``ge=1``."""
        with self.assertRaisesRegex(ValidationError, "num_randomizations"):
            TwirlingOptions(num_randomizations=0)
        # "auto" and positive ints still work.
        TwirlingOptions(num_randomizations="auto")
        TwirlingOptions(num_randomizations=64)

    def test_twirling_shots_per_randomization_must_be_positive(self):
        """``twirling.shots_per_randomization = 0`` should raise, matching legacy ``ge=1``."""
        with self.assertRaisesRegex(ValidationError, "shots_per_randomization"):
            TwirlingOptions(shots_per_randomization=0)
        TwirlingOptions(shots_per_randomization="auto")
        TwirlingOptions(shots_per_randomization=64)

    def test_measure_noise_learning_num_randomizations_must_be_positive(self):
        """``measure_noise_learning.num_randomizations = 0`` should raise (legacy ``ge=1``)."""
        with self.assertRaisesRegex(ValidationError, "num_randomizations"):
            MeasureNoiseLearningOptions(num_randomizations=0)
        MeasureNoiseLearningOptions(num_randomizations="auto")
        MeasureNoiseLearningOptions(num_randomizations=64)

    def test_pec_max_overhead_must_be_strictly_positive(self):
        """``pec.max_overhead = 0`` should raise, matching legacy ``gt=0`` (not ``ge=0``)."""
        with self.assertRaisesRegex(ValidationError, "max_overhead"):
            PecOptions(max_overhead=0)
        with self.assertRaisesRegex(ValidationError, "max_overhead"):
            PecOptions(max_overhead=-1)
        # Sane value and None (no maximum) still work.
        PecOptions(max_overhead=50)
        PecOptions(max_overhead=None)
