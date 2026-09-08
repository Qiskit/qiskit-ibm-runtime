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

"""Unit tests for EstimatorV2 TREX helper functions."""

from qiskit_ibm_runtime.executor_estimator.trex_setup import _resolve_trex_num_randomizations
from qiskit_ibm_runtime.options_models.measure_noise_learning import MeasureNoiseLearningOptions

from ...ibm_test_case import IBMTestCase


class TestResolveTrexNumRandomizations(IBMTestCase):
    """Tests for _resolve_trex_num_randomizations."""

    def test_auto_returns_twirling_value(self):
        """'auto' resolves to the twirling num_randomizations."""
        options = MeasureNoiseLearningOptions()  # num_randomizations="auto"
        self.assertEqual(_resolve_trex_num_randomizations(options, 12), 12)

    def test_explicit_int_is_returned(self):
        """An explicit int is returned unchanged, regardless of the twirling value."""
        options = MeasureNoiseLearningOptions()
        options.num_randomizations = 50
        self.assertEqual(_resolve_trex_num_randomizations(options, 12), 50)
