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

"""Tests for Options class."""

from dataclasses import asdict

from qiskit_aer.noise import NoiseModel
from qiskit.providers.fake_provider import FakeNairobiV2

from qiskit_ibm_runtime import Options, RuntimeOptions
from ..ibm_test_case import IBMTestCase
from ..utils import dict_paritally_equal, flat_dict_partially_equal, dict_keys_equal


class TestOptions(IBMTestCase):
    """Class for testing the Sampler class."""

    def test_merge_options(self):
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
                combined = Options._merge_options(asdict(options), new_ops)

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

    def test_merge_options_extra_fields(self):
        """Test merging options with extra fields."""
        options_vars = [
            (
                {
                    "initial_layout": [2, 3],
                    "transpilation": {"layout_method": "trivial"},
                    "foo": "foo",
                },
                Options(foo="foo"),  # pylint: disable=unexpected-keyword-arg
            ),
            (
                {
                    "initial_layout": [3, 4],
                    "transpilation": {"layout_method": "dense", "bar": "bar"},
                },
                Options(transpilation={"bar": "bar"}),
            ),
            (
                {
                    "initial_layout": [1, 2],
                    "foo": "foo",
                    "transpilation": {"layout_method": "dense", "foo": "foo"},
                },
                Options(  # pylint: disable=unexpected-keyword-arg
                    foo="foo", transpilation={"foo": "foo"}
                ),
            ),
        ]
        for new_ops, expected in options_vars:
            with self.subTest(new_ops=new_ops):
                options = Options()
                combined = Options._merge_options(asdict(options), new_ops)

                # Make sure the values are equal.
                self.assertTrue(
                    flat_dict_partially_equal(combined, new_ops),
                    f"new_ops={new_ops}, combined={combined}",
                )
                # Make sure the structure didn't change.
                self.assertTrue(
                    dict_keys_equal(combined, asdict(expected)),
                    f"expected={expected}, combined={combined}",
                )

    def test_runtime_options(self):
        """Test converting runtime options."""
        full_options = RuntimeOptions(
            backend="ibm_gotham",
            image="foo:bar",
            log_level="DEBUG",
            instance="h/g/p",
            job_tags=["foo", "bar"],
            max_execution_time=600,
        )
        partial_options = RuntimeOptions(backend="foo", log_level="DEBUG")

        for rt_options in [full_options, partial_options]:
            with self.subTest(rt_options=rt_options):
                self.assertGreaterEqual(
                    vars(rt_options).items(),
                    Options._get_runtime_options(vars(rt_options)).items(),
                )

    def test_program_inputs(self):
        """Test converting to program inputs."""
        noise_model = NoiseModel.from_backend(FakeNairobiV2())
        options = Options(  # pylint: disable=unexpected-keyword-arg
            optimization_level=1,
            resilience_level=2,
            transpilation={"initial_layout": [1, 2], "skip_transpilation": True},
            execution={"shots": 100},
            environment={"log_level": "DEBUG"},
            simulator={"noise_model": noise_model},
            resilience={"noise_amplifier": "GlobalFoldingAmplifier"},
            foo="foo",
        )

        inputs = Options._get_program_inputs(asdict(options))
        expected = {
            "run_options": {"shots": 100, "noise_model": noise_model},
            "transpilation_settings": {
                "optimization_settings": {"level": 1},
                "skip_transpilation": True,
                "initial_layout": [1, 2],
            },
            "resilience_settings": {
                "level": 2,
                "noise_amplifier": "GlobalFoldingAmplifier",
            },
            "foo": "foo",
        }
        self.assertTrue(
            dict_paritally_equal(inputs, expected),
            f"inputs={inputs}, expected={expected}",
        )

    def test_init_options_with_dictionary(self):
        """Test initializing options with dictionaries."""

        options_dicts = [
            {},
            {"resilience_level": 9},
            {"simulator": {"seed_simulator": 42}},
            {"resilience_level": 8, "environment": {"log_level": "WARNING"}},
            {
                "transpilation": {"initial_layout": [1, 2], "layout_method": "trivial"},
                "execution": {"shots": 100},
            },
        ]

        for opts_dict in options_dicts:
            with self.subTest(opts_dict=opts_dict):
                options = asdict(Options(**opts_dict))
                self.assertTrue(
                    dict_paritally_equal(options, opts_dict),
                    f"options={options}, opts_dict={opts_dict}",
                )

                # Make sure the structure didn't change.
                self.assertTrue(
                    dict_keys_equal(asdict(Options()), options), f"options={options}"
                )
