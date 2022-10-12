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
from ..utils import dict_paritally_equal


class TestOptions(IBMTestCase):
    """Class for testing the Sampler class."""

    def test_merge_options(self):
        """Test merging options."""
        options_vars = [
            {},
            {"resilience_level": 9},
            {"resilience_level": 9, "transpilation": {"initial_layout": [1, 2]}},
        ]
        for new_ops in options_vars:
            with self.subTest(new_ops=new_ops):
                options = Options()
                combined = options._merge_options(new_ops)
                self.assertTrue(
                    dict_paritally_equal(asdict(options), combined),
                    f"options={options}, combined={combined}",
                )

    def test_from_dict(self):
        """Test converting options from a dictionary."""
        options_vars = [
            {},
            {"resilience_level": 9},
            {"resilience_level": 9, "transpilation": {"initial_layout": [1, 2]}},
            {
                "execution": {"shots": 100},
                "environment": {"log_level": "INFO"},
            },
        ]
        for new_ops in options_vars:
            with self.subTest(new_ops=new_ops):
                options = Options._from_dict(new_ops)
                self.assertTrue(
                    dict_paritally_equal(asdict(options), new_ops),
                    f"{options} and {new_ops} not partially equal.",
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
            "resilience_settings": {"level": 2},
            "foo": "foo",
        }
        self.assertTrue(
            dict_paritally_equal(inputs, expected),
            f"inputs={inputs}, expected={expected}",
        )
