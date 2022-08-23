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

"""Tests for Session class."""

import sys
from unittest.mock import MagicMock, patch
from dataclasses import asdict

from qiskit_ibm_runtime import Sampler, Estimator, Options, RuntimeOptions, Session
from qiskit_ibm_runtime.ibm_backend import IBMBackend
from ..ibm_test_case import IBMTestCase


class TestSession(IBMTestCase):
    """Class for testing the Session class."""

    def test_run_after_close(self):
        """Test running after session is closed."""
        s = Session(service=MagicMock(), backend="ibm_gotham")
        s.close()
        with self.assertRaises(RuntimeError):
            s.run(program_id="program_id", inputs={})

    def test_missing_backend(self):
        """Test missing backend."""
        service = MagicMock()
        service.channel = "ibm_quantum"
        with self.assertRaises(ValueError):
            Session(service=service)

    def test_passing_ibm_backend(self):
        """Test passing in IBMBackend instance."""
        backend = IBMBackend(MagicMock(), MagicMock(), MagicMock())
        backend.name = "ibm_gotham"
        s = Session(service=MagicMock(), backend=backend)
        self.assertEqual(s._backend, "ibm_gotham")

    def test_run(self):
        """Test the run method."""
        job = MagicMock()
        job.job_id = "12345"
        service = MagicMock()
        service.run.return_value = job
        backend = "ibm_gotham"
        inputs = {"name": "bruce wayne"}
        options = {"log_level": "INFO"}
        program_id = "batman_begins"
        decoder = MagicMock()
        max_time = 42
        s = Session(service=service, backend=backend, max_time=max_time)
        session_ids = [None, job.job_id]
        start_sessions = [True, False]

        for idx in range(2):
            s.run(
                program_id=program_id,
                inputs=inputs,
                options=options,
                result_decoder=decoder
            )
            _, kwargs = service.run.call_args
            self.assertEqual(kwargs["program_id"], program_id)
            self.assertDictEqual(kwargs["options"], {"backend": backend, **options})
            self.assertDictEqual(kwargs["inputs"], inputs)
            self.assertEqual(kwargs["session_id"], session_ids[idx])
            self.assertEqual(kwargs["start_session"], start_sessions[idx])
            self.assertEqual(kwargs["result_decoder"], decoder)

    def test_context_manager(self):
        """Test session as a context manager."""
        pass

    def test_no_default_session(self):
        """Test no default session."""
        pass

    def test_closed_default_session(self):
        """Test default session closed."""
        pass

    def test_default_session_different_backend(self):
        """Test default session backend change."""
        pass












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
        primitives = [Sampler, Estimator]
        for cls in primitives:
            with self.subTest(primitive=cls):
                options = {"backend": "foo", "image": "foo:bar"}
                inst = cls(session=MagicMock(), options=options)
                if not isinstance(options, dict):
                    options = asdict(options)
                self.assertEqual(
                    options["image"], inst.options.experimental["image"]
                )

    @patch("qiskit_ibm_runtime.session.Session")
    def test_default_session(self, _):
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
