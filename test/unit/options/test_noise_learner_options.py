# This code is part of Qiskit.
#
# (C) Copyright IBM 2024-2026.
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
from typing import Any

import pytest
from pydantic import ValidationError

from qiskit_ibm_runtime.options import NoiseLearnerOptions

from ...asserts import (
    assert_dict_flat_partially_equal,
    assert_dict_keys_equal,
    assert_dict_partially_equal,
)


class TestNoiseLearnerOptions:
    """Class for testing the NoiseLearnerOptions class."""

    @pytest.mark.parametrize(
        "val",
        [
            ({"max_layers_to_learn": -1}, "max_layers_to_learn must be >=0"),
            ({"shots_per_randomization": 0}, "shots_per_randomization must be >=1"),
            ({"num_randomizations": 0}, "num_randomizations must be >=1"),
            ({"layer_pair_depths": [-2, 0, 0]}, "must all be >= 0"),
            (
                {"twirling_strategy": "my_strategy"},
                "'active', 'active-accum', 'active-circuit' or 'all'",
            ),
        ],
    )
    def test_bad_inputs(self, val: tuple[dict[str, Any], str]) -> None:
        """Test invalid inputs."""
        bad_input, error_msg = val
        with pytest.raises(ValidationError, match=error_msg):
            NoiseLearnerOptions(**bad_input)

    @pytest.mark.parametrize(
        "opts_dict",
        [
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
        ],
    )
    def test_init_options_with_dictionary(self, opts_dict: dict[str, Any]) -> None:
        """Test initializing options with dictionaries."""
        options = asdict(NoiseLearnerOptions(**opts_dict))
        assert_dict_partially_equal(options, opts_dict)
        assert_dict_keys_equal(asdict(NoiseLearnerOptions()), options)

    @pytest.mark.parametrize(
        "new_opts",
        [
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
        ],
    )
    def test_update_options(self, new_opts: dict[str, Any]) -> None:
        """Test update method."""
        options = NoiseLearnerOptions()
        options.update(**new_opts)

        # Make sure the values are equal.
        assert_dict_flat_partially_equal(asdict(options), new_opts)
        # Make sure the structure didn't change.
        assert_dict_keys_equal(asdict(options), asdict(NoiseLearnerOptions()))
