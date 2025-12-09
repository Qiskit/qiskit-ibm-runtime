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

"""Tests the classes `NoiseLearnerV3Result` and `NoiseLearnerV3Results`."""

import numpy as np

from qiskit.quantum_info import QubitSparsePauliList

from qiskit_ibm_runtime.noise_learner_v3.noise_learner_v3_result import NoiseLearnerV3Result

from ...ibm_test_case import IBMTestCase


class TestNoiseLearnerV3Result(IBMTestCase):
    """Tests the `NoiseLearnerV3Result` class."""

    def test_from_generators_valid_input(self):
        generators =  [QubitSparsePauliList.from_label(pauli1 + pauli0) for pauli1 in "IXYZ" for pauli0 in "IXYZ"][1:]
        rates = [0.02452, 0., 0.00324, 0., 0., 0.0006, 0., 0., 0.0006, 0., 0., 0., 0.02452, 0., 0.00071]
        rates_std = np.arange(0, 0.15, 0.01)
        metadata = {"learning_protocol": "lindblad"}
        result = NoiseLearnerV3Result.from_generators(generators, rates, rates_std, metadata)
        self.assertEqual(generators, result._generators)
        self.assertTrue(np.array_equal(np.array(rates), result._rates))
        self.assertTrue(np.array_equal(rates_std, result._rates_std))
        self.assertEqual(metadata, result.metadata)