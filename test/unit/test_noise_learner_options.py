# This code is part of Qiskit.
#
# (C) Copyright IBM 2024.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Tests for NoiseLearnerOptions class."""

from dataclasses import asdict

from ddt import data, ddt
from pydantic import ValidationError

from qiskit_ibm_runtime.options import NoiseLearnerOptions

from ..ibm_test_case import IBMTestCase
from ..utils import dict_keys_equal, dict_paritally_equal, flat_dict_partially_equal


@ddt
class TestEstimatorOptions(IBMTestCase):
    """Class for testing the EstimatorOptions class."""

    @data(
        ({"max_layers_to_learn": -1}, "max_layers_to_learn must be >=0"),
        ({"shots_per_randomization": 0}, "shots_per_randomization must be >=1"),
        ({"num_randomizations": 0}, "num_randomizations must be >=1"),
        ({"layer_pair_depths": [-2, 0, 0]}, "must all be >= 0"),
        (
            {"twirling_strategy": "my_strategy"},
            "'active', 'active-accum', 'active-circuit' or 'all'",
        ),
    )
    def test_bad_inputs(self, val):
        """Test invalid inputs."""
        bad_input, error_msg = val
        with self.assertRaisesRegex(ValidationError, error_msg):
            NoiseLearnerOptions(**bad_input)

    @data(
        {},
        {"max_layers_to_learn": 5},
        {"shots_per_randomization": 20},
        {"num_randomizations": 1, "environment": {"log_level": "WARNING"}},
        {"layer_pair_depths": [0, 2, 4]},
        {"twirling_strategy": "all"},
        {
            "environment": {"log_level": "ERROR"},
            "shots_per_randomization": 20,
            "max_layers_to_learn": 5,
        },
    )
    def test_init_options_with_dictionary(self, opts_dict):
        """Test initializing options with dictionaries."""
        options = asdict(NoiseLearnerOptions(**opts_dict))
        self.assertTrue(
            dict_paritally_equal(options, opts_dict),
            f"options={options}, opts_dict={opts_dict}",
        )

        self.assertTrue(
            dict_keys_equal(asdict(NoiseLearnerOptions()), options), f"options={options}"
        )

    @data(
        {},
        {"max_layers_to_learn": 5},
        {"shots_per_randomization": 20},
        {"num_randomizations": 1, "environment": {"log_level": "WARNING"}},
        {"layer_pair_depths": [0, 2, 4]},
        {"twirling_strategy": "all"},
        {
            "environment": {"log_level": "ERROR"},
            "shots_per_randomization": 20,
            "max_layers_to_learn": 5,
        },
    )
    def test_update_options(self, new_opts):
        """Test update method."""
        options = NoiseLearnerOptions()
        options.update(**new_opts)

        # Make sure the values are equal.
        self.assertTrue(
            flat_dict_partially_equal(asdict(options), new_opts),
            f"new_opts={new_opts}, combined={options}",
        )
        # Make sure the structure didn't change.
        self.assertTrue(dict_keys_equal(asdict(options), asdict(NoiseLearnerOptions())))
