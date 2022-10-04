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
            {"resilience_level": 9, "transpilation": {"seed_transpiler": 24}},
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
            {"resilience_level": 9, "transpilation": {"seed_transpiler": 24}},
            {
                "execution": {"shots": 100},
                "environment": {"image": "foo:bar", "log_level": "INFO"},
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
        rt_options = RuntimeOptions(backend="foo", log_level="DEBUG")
        self.assertGreaterEqual(
            vars(rt_options).items(),
            Options._get_runtime_options(vars(rt_options)).items(),
        )
