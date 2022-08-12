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

"""Tests for primitive classes."""

import sys
from unittest.mock import MagicMock, patch
from dataclasses import asdict

from qiskit_ibm_runtime import Sampler, Estimator, Options, RuntimeOptions
from ..ibm_test_case import IBMTestCase


class TestPrimitives(IBMTestCase):
    """Class for testing the Sampler class."""

    def test_skip_transpilation(self):
        """Test skip_transpilation is hornored."""
        primitives = [Sampler, Estimator]
        for cls in primitives:
            with self.subTest(primitive=cls):
                inst = cls(session=MagicMock(), skip_transpilation=True)
                self.assertTrue(inst.options.transpilation.skip_transpilation)

    def test_skip_transpilation_overwrite(self):
        """Test overwriting skip_transpilation."""
        options = Options()
        options.transpilation.skip_transpilation = False
        primitives = [Sampler, Estimator]
        for cls in primitives:
            with self.subTest(primitive=cls):
                inst = cls(
                    session=MagicMock(), options=options, skip_transpilation=True
                )
                self.assertFalse(inst.options.transpilation.skip_transpilation)

    def test_dict_options(self):
        """Test passing a dictionary as options."""
        options_vars = [
            {},
            {
                "resilience_level": 1,
                "transpilation": {"seed_transpiler": 24},
                "execution": {"shots": 100, "init_qubits": True},
            },
            {"transpilation": {}},
        ]
        primitives = [Sampler, Estimator]
        for cls in primitives:
            for options in options_vars:
                with self.subTest(primitive=cls, options=options):
                    inst = cls(session=MagicMock(), options=options)
                    expected = asdict(Options())
                    self._update_dict(expected, options)
                    self.assertDictEqual(expected, asdict(inst.options))

    def test_runtime_options(self):
        """Test passing in runtime options."""
        options_vars = [
            {"backend_name": "foo", "image": "foo:bar"},
            RuntimeOptions(backend_name="foo", image="foo:bar"),
        ]
        primitives = [Sampler, Estimator]
        for cls in primitives:
            for options in options_vars:
                with self.subTest(primitive=cls, options=options):
                    inst = cls(session=MagicMock(), options=options)
                    if not isinstance(options, dict):
                        options = asdict(options)
                    self.assertEqual(options["backend_name"], inst.options.backend)
                    self.assertEqual(
                        options["image"], inst.options.experimental["image"]
                    )

    @patch("qiskit_ibm_runtime.estimator.Session")
    @patch("qiskit_ibm_runtime.sampler.Session")
    def test_default_session(self, *_):
        """Test a session is created if not passed in."""
        sampler = Sampler()
        self.assertIsNotNone(sampler.session)
        estimator = Estimator()
        self.assertEqual(estimator.session, sampler.session)

    def test_run_inputs_default(self):
        """Test run using default options."""
        session = MagicMock()
        options_vars = [
            (Options(resilience_level=9), {"resilience_settings": {"level": 9}}),
            (
                Options(optimization_level=8),
                {"transpilation_settings": {"optimization_settings": {"level": 8}}},
            ),
            (
                {"transpilation": {"seed_transpiler": 24}, "execution": {"shots": 100}},
                {
                    "transpilation_settings": {"seed_transpiler": 24},
                    "run_options": {"shots": 100},
                },
            ),
        ]
        primitives = [Sampler, Estimator]
        for cls in primitives:
            for options, expected in options_vars:
                with self.subTest(primitive=cls, options=options):
                    inst = cls(session=session, options=options)
                    inst.run(MagicMock(), MagicMock())
                    if sys.version_info >= (3, 8):
                        inputs = session.run.call_args.kwargs["inputs"]
                    else:
                        _, kwargs = session.run.call_args
                        inputs = kwargs["inputs"]

                    self._assert_dict_paritally_equal(inputs, expected)

    def test_run_inputs_updated_default(self):
        """Test run using updated default options."""
        session = MagicMock()
        primitives = [Sampler, Estimator]
        for cls in primitives:
            with self.subTest(primitive=cls):
                inst = cls(session=session)
                inst.options.resilience_level = 1
                inst.options.optimization_level = 2
                inst.options.execution.shots = 3
                inst.run(MagicMock(), MagicMock())
                if sys.version_info >= (3, 8):
                    inputs = session.run.call_args.kwargs["inputs"]
                else:
                    _, kwargs = session.run.call_args
                    inputs = kwargs["inputs"]
                self._assert_dict_paritally_equal(
                    inputs,
                    {
                        "resilience_settings": {"level": 1},
                        "transpilation_settings": {
                            "optimization_settings": {"level": 2}
                        },
                        "run_options": {"shots": 3},
                    },
                )

    def test_run_inputs_overwrite(self):
        """Test run using overwritten options."""
        session = MagicMock()
        options_vars = [
            ({"resilience_level": 9}, {"resilience_settings": {"level": 9}}),
            ({"shots": 200}, {"run_options": {"shots": 200}}),
            (
                {"optimization_level": 8},
                {"transpilation_settings": {"optimization_settings": {"level": 8}}},
            ),
            (
                {"seed_transpiler": 24, "optimization_level": 8},
                {
                    "transpilation_settings": {
                        "optimization_settings": {"level": 8},
                        "seed_transpiler": 24,
                    }
                },
            ),
        ]
        primitives = [Sampler, Estimator]
        for cls in primitives:
            for options, expected in options_vars:
                with self.subTest(primitive=cls, options=options):
                    inst = cls(session=session)
                    inst.run(MagicMock(), MagicMock(), **options)
                    if sys.version_info >= (3, 8):
                        inputs = session.run.call_args.kwargs["inputs"]
                    else:
                        _, kwargs = session.run.call_args
                        inputs = kwargs["inputs"]
                    self._assert_dict_paritally_equal(inputs, expected)
                    self.assertDictEqual(asdict(inst.options), asdict(Options()))

    def _update_dict(self, dict1, dict2):
        for key, val in dict1.items():
            if isinstance(val, dict):
                self._update_dict(val, dict2.pop(key, {}))
            elif key in dict2.keys():
                dict1[key] = dict2.pop(key)

    def _assert_dict_paritally_equal(self, dict1, dict2):
        for key, val in dict2.items():
            if isinstance(val, dict):
                self._assert_dict_paritally_equal(dict1.get(key), val)
            elif key in dict1:
                self.assertEqual(val, dict1[key])
