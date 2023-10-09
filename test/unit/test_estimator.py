# This code is part of Qiskit.
#
# (C) Copyright IBM 2021.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Tests for estimator class."""

import warnings

from qiskit import QuantumCircuit
from qiskit.quantum_info import SparsePauliOp

from qiskit_ibm_runtime import Estimator, Options

from ..ibm_test_case import IBMTestCase
from ..utils import get_mocked_backend


class TestEstimator(IBMTestCase):
    """Class for testing the Estimator class."""

    def setUp(self) -> None:
        super().setUp()
        self.circuit = QuantumCircuit(1, 1)
        self.observables = SparsePauliOp.from_list([("I", 1)])

    def test_unsupported_values_for_estimator_options(self):
        """Test exception when options levels are not supported."""
        options_bad = [
            {"resilience_level": 4, "optimization_level": 3},
            {"optimization_level": 4, "resilience_level": 2},
        ]

        for bad_opt in options_bad:
            estimator = Estimator(backend=get_mocked_backend(), options=bad_opt)
            with self.assertRaises(ValueError) as exc:
                _ = estimator.run(self.circuit, observables=self.observables, **bad_opt)
            self.assertIn(list(bad_opt.keys())[0], str(exc.exception))

    def test_deprecated_noise_amplifier(self):
        """Test noise_amplifier deprecation."""
        opt = Options()
        opt.resilience.noise_amplifier = "GlobalFoldingAmplifier"

        with warnings.catch_warnings(record=True) as warn:
            warnings.simplefilter("always")
            estimator = Estimator(backend=get_mocked_backend(), options=opt)
            estimator.run(self.circuit, self.observables)
            self.assertEqual(len(warn), 1, "Deprecation warning not found.")
            self.assertIn("noise_amplifier", str(warn[-1].message))

    def test_deprecated_noise_amplifier_run(self):
        """Test noise_amplifier deprecation in run."""

        with warnings.catch_warnings(record=True) as warn:
            warnings.simplefilter("always")
            estimator = Estimator(backend=get_mocked_backend())
            estimator.run(self.circuit, self.observables, noise_amplifier="GlobalFoldingAmplifier")
            self.assertEqual(len(warn), 1, "Deprecation warning not found.")
            self.assertIn("noise_amplifier", str(warn[-1].message))
