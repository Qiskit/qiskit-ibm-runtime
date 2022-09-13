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
from unittest.mock import MagicMock, patch, ANY
from dataclasses import asdict

from qiskit.test.reference_circuits import ReferenceCircuits
from qiskit.quantum_info import SparsePauliOp
from qiskit_ibm_runtime import Sampler, Estimator, Options, Session
from qiskit_ibm_runtime.ibm_backend import IBMBackend
import qiskit_ibm_runtime.session as session_pkg
from ..ibm_test_case import IBMTestCase
from ..utils import dict_paritally_equal


class TestPrimitives(IBMTestCase):
    """Class for testing the Sampler class."""

    @classmethod
    def setUpClass(cls):
        cls.qx = ReferenceCircuits.bell()
        cls.obs = SparsePauliOp.from_list([("IZ", 1)])
        return super().setUpClass()

    def tearDown(self) -> None:
        super().tearDown()
        session_pkg._DEFAULT_SESSION = None

    def test_skip_transpilation(self):
        """Test skip_transpilation is hornored."""
        primitives = [Sampler, Estimator]
        for cls in primitives:
            with self.subTest(primitive=cls):
                inst = cls(session=MagicMock(spec=Session), skip_transpilation=True)
                self.assertTrue(inst.options.transpilation.skip_transpilation)

    def test_skip_transpilation_overwrite(self):
        """Test overwriting skip_transpilation."""
        options = Options()
        options.transpilation.skip_transpilation = False
        primitives = [Sampler, Estimator]
        for cls in primitives:
            with self.subTest(primitive=cls):
                inst = cls(
                    session=MagicMock(spec=Session),
                    options=options,
                    skip_transpilation=True,
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
                "log_level": "INFO",
            },
            {"transpilation": {}},
        ]
        primitives = [Sampler, Estimator]
        for cls in primitives:
            for options in options_vars:
                with self.subTest(primitive=cls, options=options):
                    inst = cls(session=MagicMock(spec=Session), options=options)
                    expected = asdict(Options())
                    self._update_dict(expected, options)
                    self.assertDictEqual(expected, asdict(inst.options))

    def test_backend_in_options(self):
        """Test specifying backend in options."""
        primitives = [Sampler, Estimator]
        backend_name = "ibm_gotham"
        backend = MagicMock(spec=IBMBackend)
        backend.name = backend_name
        backends = [backend_name, backend]
        for cls in primitives:
            for backend in backends:
                with self.subTest(primitive=cls, backend=backend):
                    options = {"backend": backend}
                    inst = cls(service=MagicMock(), options=options)
                    self.assertEqual(inst.session.backend(), backend_name)

    def test_options_copied(self):
        """Test modifying original options does not affect primitives."""
        options = Options()
        primitives = [Sampler, Estimator]
        for cls in primitives:
            with self.subTest(primitive=cls):
                options.transpilation.skip_transpilation = True
                inst = cls(session=MagicMock(spec=Session), options=options)
                options.transpilation.skip_transpilation = False
                self.assertTrue(inst.options.transpilation.skip_transpilation)

    @patch("qiskit_ibm_runtime.session.Session")
    @patch("qiskit_ibm_runtime.session.QiskitRuntimeService")
    def test_default_session(self, *_):
        """Test a session is created if not passed in."""
        try:
            sampler = Sampler()
            self.assertIsNotNone(sampler.session)
            estimator = Estimator()
            self.assertEqual(estimator.session, sampler.session)
        finally:
            # Ensure it's cleaned up or next test will fail.
            session_pkg._DEFAULT_SESSION = None

    def test_default_session_after_close(self):
        """Test a new default session is open after previous is closed."""
        service = MagicMock()
        sampler = Sampler(service=service)
        sampler.session.close()
        estimator = Estimator(service=service)
        self.assertIsNotNone(estimator.session)
        self.assertTrue(estimator.session._active)
        self.assertNotEqual(estimator.session, sampler.session)

    @patch("qiskit_ibm_runtime.session.Session")
    @patch("qiskit_ibm_runtime.session.QiskitRuntimeService")
    def test_backend_str_as_session(self, _, mock_session):
        """Test specifying a backend name as session."""
        primitives = [Sampler, Estimator]
        backend_name = "ibm_gotham"

        for cls in primitives:
            with self.subTest(primitive=cls):
                _ = cls(session=backend_name)
                mock_session.assert_called_with(service=ANY, backend=backend_name)

    def test_backend_as_session(self):
        """Test specifying a backend as session."""
        primitives = [Sampler, Estimator]
        backend = MagicMock(spec=IBMBackend)
        backend.name = "ibm_gotham"
        backend.service = MagicMock()

        for cls in primitives:
            with self.subTest(primitive=cls):
                inst = cls(session=backend)
                self.assertEqual(inst.session.backend(), backend.name)

    def test_default_session_context_manager(self):
        """Test getting default session within context manager."""
        service = MagicMock()
        backend = "ibm_gotham"
        primitives = [Sampler, Estimator]

        for cls in primitives:
            with self.subTest(primitive=cls):
                with Session(service=service, backend=backend) as session:
                    inst = cls()
                    self.assertEqual(inst.session, session)
                    self.assertEqual(inst.session.backend(), backend)

    def test_default_session_cm_new_backend(self):
        """Test using a different backend within context manager."""
        service = MagicMock()
        backend = MagicMock(spec=IBMBackend)
        backend.name = "ibm_gotham"
        backend.service = service
        cm_backend = "ibm_metropolis"
        primitives = [Sampler, Estimator]

        for cls in primitives:
            with self.subTest(primitive=cls):
                with Session(service=service, backend=cm_backend) as session:
                    inst = cls(session=backend)
                    self.assertNotEqual(inst.session, session)
                    self.assertEqual(inst.session.backend(), backend.name)
                    self.assertEqual(session.backend(), cm_backend)
                    self.assertTrue(session._active)
                    inst2 = cls()
                    self.assertEqual(inst2.session, session)
                self.assertFalse(session._active)

    def test_run_default_options(self):
        """Test run using default options."""
        session = MagicMock(spec=Session)
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
                    inst.run(self.qx, observables=self.obs)
                    if sys.version_info >= (3, 8):
                        inputs = session.run.call_args.kwargs["inputs"]
                    else:
                        _, kwargs = session.run.call_args
                        inputs = kwargs["inputs"]

                    self._assert_dict_paritally_equal(inputs, expected)

    def test_run_updated_default_options(self):
        """Test run using updated default options."""
        session = MagicMock(spec=Session)
        primitives = [Sampler, Estimator]
        for cls in primitives:
            with self.subTest(primitive=cls):
                inst = cls(session=session)
                inst.options.resilience_level = 1
                inst.options.optimization_level = 2
                inst.options.execution.shots = 3
                inst.run(self.qx, observables=self.obs)
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

    def test_run_overwrite_options(self):
        """Test run using overwritten options."""
        session = MagicMock(spec=Session)
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
                    inst.run(self.qx, observables=self.obs, **options)
                    if sys.version_info >= (3, 8):
                        inputs = session.run.call_args.kwargs["inputs"]
                    else:
                        _, kwargs = session.run.call_args
                        inputs = kwargs["inputs"]
                    self._assert_dict_paritally_equal(inputs, expected)
                    self.assertDictEqual(asdict(inst.options), asdict(Options()))

    def test_run_multiple_different_options(self):
        """Test multiple runs with different options."""
        session = MagicMock(spec=Session)
        primitives = [Sampler, Estimator]
        for cls in primitives:
            with self.subTest(primitive=cls):
                inst = cls(session=session)
                inst.run(self.qx, observables=self.obs, shots=100)
                inst.run(self.qx, observables=self.obs, shots=200)
                kwargs_list = session.run.call_args_list
                for idx, shots in zip([0, 1], [100, 200]):
                    self.assertEqual(
                        kwargs_list[idx][1]["inputs"]["run_options"]["shots"], shots
                    )
                self.assertDictEqual(asdict(inst.options), asdict(Options()))

    def test_run_same_session(self):
        """Test multiple runs within a session."""
        num_runs = 5
        primitives = [Sampler, Estimator]
        session = MagicMock(spec=Session)
        for idx in range(num_runs):
            cls = primitives[idx % 2]
            inst = cls(session=session)
            inst.run(self.qx, observables=self.obs)
        self.assertEqual(session.run.call_count, num_runs)

    def _update_dict(self, dict1, dict2):
        for key, val in dict1.items():
            if isinstance(val, dict):
                self._update_dict(val, dict2.pop(key, {}))
            elif key in dict2.keys():
                dict1[key] = dict2.pop(key)

    def _assert_dict_paritally_equal(self, dict1, dict2):
        self.assertTrue(
            dict_paritally_equal(dict1, dict2),
            f"{dict1} and {dict2} not partially equal.",
        )
