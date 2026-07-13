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

"""Tests for EstimatorOptions."""

from qiskit_ibm_runtime.options_models.dynamical_decoupling_options import (
    DynamicalDecouplingOptions,
)
from qiskit_ibm_runtime.options_models.environment_options import EnvironmentOptions
from qiskit_ibm_runtime.options_models.estimator_options import EstimatorOptions
from qiskit_ibm_runtime.options_models.execution_options import ExecutionOptions

from ...ibm_test_case import IBMTestCase


class TestEstimatorOptions(IBMTestCase):
    """Tests for EstimatorOptions."""

    def test_default_values(self):
        """Test default values."""
        options = EstimatorOptions()
        self.assertEqual(options.default_precision, 0.015625)
        self.assertIsInstance(options.dynamical_decoupling, DynamicalDecouplingOptions)
        self.assertIsInstance(options.execution, ExecutionOptions)
        self.assertEqual(options.experimental, {})
        self.assertIsNone(options.max_execution_time)
        self.assertIsInstance(options.environment, EnvironmentOptions)
        self.assertIsNone(options.resilience.measure_mitigation)
        self.assertEqual(options.resilience.measure_noise_learning.num_randomizations, 32)
        self.assertEqual(options.resilience.measure_noise_learning.shots_per_randomization, "auto")
