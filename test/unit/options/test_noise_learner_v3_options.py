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

from ...ibm_test_case import IBMTestCase


class TestNoiseLearnerV3Options(IBMTestCase):
    """Tests the ``NoiseLearnerV3Options`` class."""

    def test_to_options_model(self):
        """Test the ``NoiseLearnerV3Options.to_options_model`` method."""
        options = NoiseLearnerV3Options()
        options.num_randomizations = 15
        options.experimental = {"not": "me"}

        options_model = options.to_options_model("v0.1")
        self.assertEqual(options_model.num_randomizations, 15)

    def test_to_options_model_invalid_schema_model(self):
        """Test that ``NoiseLearnerV3Options.to_options_model`` raises for a
        non-existing schema version"""
        options = NoiseLearnerV3Options()
        options.num_randomizations = 15
        options.experimental = {"not": "me"}

        with self.assertRaisesRegex(ValueError, "No option model found"):
            options.to_options_model("non-existing schema version")

    def test_to_runtime_options(self):
        """Test the ``NoiseLearnerV3Options.to_runtime_options`` method."""
        options = NoiseLearnerV3Options()
        options.num_randomizations = 15
        options.environment = {"private": True}

        runtime_options = options.to_runtime_options()
        self.assertNotIn("num_randomizations", runtime_options)
        self.assertEqual(runtime_options["private"], True)
        self.assertEqual(runtime_options["max_execution_time"], None)
