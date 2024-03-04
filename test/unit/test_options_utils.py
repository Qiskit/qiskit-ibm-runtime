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

"""Tests for options.utils."""

from dataclasses import asdict

from ddt import data, ddt

from qiskit_ibm_runtime import Options
from qiskit_ibm_runtime.options.utils import (
    merge_options,
    Unset,
    remove_dict_unset_values,
    remove_empty_dict,
)
from qiskit_ibm_runtime.options import EstimatorOptions, SamplerOptions

from ..ibm_test_case import IBMTestCase
from ..utils import dict_keys_equal, flat_dict_partially_equal


@ddt
class TestOptionsUtils(IBMTestCase):
    """Class for testing the options.utils."""

    def test_merge_v1options(self):
        """Test merging options."""
        options_vars = [
            {},
            {"resilience_level": 9},
            {"resilience_level": 8, "transpilation": {"initial_layout": [1, 2]}},
            {"shots": 99, "seed_simulator": 42},
            {"resilience_level": 99, "shots": 98, "initial_layout": [3, 4]},
            {
                "initial_layout": [1, 2],
                "transpilation": {"layout_method": "trivial"},
                "log_level": "INFO",
            },
        ]
        for new_ops in options_vars:
            with self.subTest(new_ops=new_ops):
                options = Options()
                combined = merge_options(asdict(options), new_ops)

                # Make sure the values are equal.
                self.assertTrue(
                    flat_dict_partially_equal(combined, new_ops),
                    f"new_ops={new_ops}, combined={combined}",
                )
                # Make sure the structure didn't change.
                self.assertTrue(
                    dict_keys_equal(combined, asdict(options)),
                    f"options={options}, combined={combined}",
                )

    def test_merge_estimator_options(self):
        """Test merging estimator options."""
        options_vars = [
            {},
            {"resilience_level": 9},
            {"default_shots": 99, "seed_simulator": 42},
            {"resilience_level": 99, "default_shots": 98},
            {
                "optimization_level": 1,
                "log_level": "INFO",
            },
            # TODO: Re-enable when flat merge is disabled
            # {
            #     "resilience": {
            #         "measure_noise_learning": {"num_randomizations": 1},
            #         "zne": {"extrapolator": "linear"},
            #     }
            # },
        ]
        for new_ops in options_vars:
            with self.subTest(new_ops=new_ops):
                options = EstimatorOptions()
                combined = merge_options(asdict(options), new_ops)

                # Make sure the values are equal.
                self.assertTrue(
                    flat_dict_partially_equal(combined, new_ops),
                    f"new_ops={new_ops}, combined={combined}",
                )
                # Make sure the structure didn't change.
                self.assertTrue(
                    dict_keys_equal(combined, asdict(options)),
                    f"options={options}, combined={combined}",
                )

    @data(
        {},
        {"default_shots": 1000},
        {"log_level": "INFO", "dynamical_decoupling": {"enable": True}},
        {"execution": {"init_qubits": False}},
    )
    def test_merge_sampler_options(self, new_ops):
        """Test merging sampler options."""
        options = SamplerOptions()
        combined = merge_options(asdict(options), new_ops)

        # Make sure the values are equal.
        self.assertTrue(
            flat_dict_partially_equal(combined, new_ops),
            f"new_ops={new_ops}, combined={combined}",
        )
        # Make sure the structure didn't change.
        self.assertTrue(
            dict_keys_equal(combined, asdict(options)),
            f"options={options}, combined={combined}",
        )

    @data(
        ({"foo": 1, "bar": Unset}, {"foo": 1}),
        ({"foo": 1, "bar": 2}, {"foo": 1, "bar": 2}),
        ({"foo": {"bar": Unset}}, {"foo": {}}),
        ({"foo": False}, {"foo": False}),
    )
    def test_remove_dict_unset_values(self, in_vals):
        """Test removing dictionary with unset values."""
        in_dict, expected = in_vals
        remove_dict_unset_values(in_dict)
        self.assertDictEqual(in_dict, expected)

    @data(
        ({"foo": 1, "bar": {}}, {"foo": 1}),
        ({"foo": 1, "bar": 2}, {"foo": 1, "bar": 2}),
        ({"foo": {"bar": {}}}, {}),
        ({"foo": {"bar": {"foobar": {}}}}, {}),
    )
    def test_remove_empty_dict(self, in_vals):
        """Test removing empty dict."""
        in_dict, expected = in_vals
        remove_empty_dict(in_dict)
        self.assertDictEqual(in_dict, expected)
