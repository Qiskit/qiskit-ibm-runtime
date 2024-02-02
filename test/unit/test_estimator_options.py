# This code is part of Qiskit.
#
# (C) Copyright IBM 2023.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Tests for Options class."""

from ddt import data, ddt
from pydantic import ValidationError

from qiskit_ibm_runtime.options import EstimatorOptions

from ..ibm_test_case import IBMTestCase


@ddt
class TestEStimatorOptions(IBMTestCase):
    """Class for testing the Sampler class."""

    @data(
        {"resilience_level": 99},
        {"dynamical_decoupling": "foo"},
        {"transpilation": {"skip_transpilation": "foo"}},
        {"execution": {"shots": 0}},
        {"twirling": {"strategy": "foo"}},
        {"transpilation": {"foo": "bar"}},
        {"zne_noise_factors": [0.5]},
        {"noise_factors": [1, 3, 5]},
        {"zne_extrapolator": "exponential", "zne_noise_factors": [1]},
        {"zne_mitigation": True, "pec_mitigation": True},
        {"simulator": {"noise_model": "foo"}},
    )
    def test_bad_inputs(self, val):
        """Test invalid inputs."""
        with self.assertRaises(ValidationError) as exc:
            EstimatorOptions(**val)
        self.assertIn(list(val.keys())[0], str(exc.exception))
