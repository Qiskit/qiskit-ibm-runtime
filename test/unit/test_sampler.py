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

"""Tests for sampler class."""

from qiskit.test.reference_circuits import ReferenceCircuits
from qiskit_ibm_runtime import Sampler

from ..ibm_test_case import IBMTestCase
from ..utils import get_mocked_backend


class TestSampler(IBMTestCase):
    """Class for testing the Sampler class."""

    def test_unsupported_values_for_sampler_options(self):
        """Test exception when options levels are not supported."""
        options_bad = [
            {"resilience_level": 2, "optimization_level": 3},
            {"optimization_level": 4, "resilience_level": 1},
        ]

        circuit = ReferenceCircuits.bell()
        for bad_opt in options_bad:
            inst = Sampler(backend=get_mocked_backend())
            with self.assertRaises(ValueError) as exc:
                _ = inst.run(circuit, **bad_opt)
            self.assertIn(list(bad_opt.keys())[0], str(exc.exception))
