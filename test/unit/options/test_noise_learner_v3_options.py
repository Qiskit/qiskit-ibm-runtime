# This code is part of Qiskit.
#
# (C) Copyright IBM 2025.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Tests the ``NoiseLearnerV3Options`` class."""

from qiskit_ibm_runtime.options.noise_learner_v3_options import NoiseLearnerV3Options
from qiskit_ibm_runtime.options.utils import Unset

from ...ibm_test_case import IBMTestCase


class TestNoiseLearnerV3Options(IBMTestCase):
    """Tests the ``NoiseLearnerV3Options`` class."""

    def test_to_options_model(self):
        """Test the ``NoiseLearnerV3Options.to_options_model`` method."""
        options = NoiseLearnerV3Options(num_randomizations=15, experimental={"not": "me"})
        options_model = options.to_options_model("v0.1")
        self.assertEqual(options_model.num_randomizations, 15)