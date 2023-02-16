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
import copy
import json
from unittest.mock import MagicMock, patch, ANY
import warnings
from dataclasses import asdict
from typing import Dict
import unittest

from qiskit.circuit import QuantumCircuit
from qiskit.circuit.library import RealAmplitudes
from qiskit.test.reference_circuits import ReferenceCircuits
from qiskit.quantum_info import SparsePauliOp
from qiskit.primitives.utils import _circuit_key

from qiskit_ibm_runtime import Sampler, Estimator, Options, Session, RuntimeEncoder
from qiskit_ibm_runtime.ibm_backend import IBMBackend
import qiskit_ibm_runtime.session as session_pkg
from qiskit_ibm_runtime.utils.utils import _hash

from ..ibm_test_case import IBMTestCase
from ..utils import dict_paritally_equal, flat_dict_partially_equal, dict_keys_equal
from .mock.fake_runtime_service import FakeRuntimeService


class MockSession(Session):
    """Mock for session class"""

    _circuits_map: Dict[str, QuantumCircuit] = {}


class TestPrimitives(IBMTestCase):
    """Class for testing the Sampler and Estimator classes."""

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
                inst = cls(session=MagicMock(spec=MockSession), skip_transpilation=True)
                self.assertTrue(
                    inst.options.get("transpilation").get("skip_transpilation")
                )

    def test_skip_transpilation_overwrite(self):
        """Test overwriting skip_transpilation."""
        options = Options()
        options.transpilation.skip_transpilation = False
        primitives = [Sampler, Estimator]
        for cls in primitives:
            with self.subTest(primitive=cls):
                inst = cls(
                    session=MagicMock(spec=MockSession),
                    options=options,
                    skip_transpilation=True,
                )
                self.assertFalse(
                    inst.options.get("transpilation").get("skip_transpilation")
                )

    def test_dict_options(self):
        """Test passing a dictionary as options."""
        options_vars = [
            {},
            {
                "resilience_level": 1,
                "transpilation": {"initial_layout": [1, 2]},
                "execution": {"shots": 100, "init_qubits": True},
            },
            {"optimization_level": 2},
            {"transpilation": {}},
        ]
        primitives = [Sampler, Estimator]
        for cls in primitives:
            for options in options_vars:
                with self.subTest(primitive=cls, options=options):
                    inst = cls(session=MagicMock(spec=MockSession), options=options)
                    expected = asdict(Options())
                    self._update_dict(expected, copy.deepcopy(options))
                    # for resilience_level and optimization_level, if given by the user,
                    # maintain value. Otherwise, set default as given in Sampler/Estimator
                    if not options.get("resilience_level"):
                        expected["resilience_level"] = 0
                    if not options.get("optimization_level"):
                        expected["optimization_level"] = 1
                    self.assertDictEqual(expected, inst.options.__dict__)

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
                    with warnings.catch_warnings(record=True) as warn:
                        warnings.simplefilter("always")
                        inst = cls(service=MagicMock(), options=options)
                        # We'll get 2 deprecation warnings - one for service and one for backend.
                        # We need service otherwise backend will get ignored.
                        self.assertEqual(len(warn), 2)
                        self.assertTrue(
                            all(
                                issubclass(one_warn.category, DeprecationWarning)
                                for one_warn in warn
                            )
                        )
                    self.assertEqual(inst.session.backend(), backend_name)

    def test_old_options(self):
        """Test specifying old runtime options."""
        primitives = [Sampler, Estimator]
        session = MagicMock(spec=MockSession)
        options = [{"log_level": "WARNING"}, {"image": "foo:bar"}]

        for cls in primitives:
            for opt in options:
                with self.subTest(primitive=cls, options=opt):
                    inst = cls(session=session, options=opt)
                    inst.run(self.qx, observables=self.obs)
                    _, kwargs = session.run.call_args
                    run_options = kwargs["options"]
                    for key, val in opt.items():
                        self.assertEqual(run_options[key], val)
                    inputs = kwargs["inputs"]
                    self.assertTrue(all(key not in inputs.keys() for key in opt))

    def test_runtime_options(self):
        """Test RuntimeOptions specified as primitive options."""
        session = MagicMock(spec=MockSession)
        primitives = [Sampler, Estimator]
        env_vars = [
            {"log_level": "DEBUG"},
            {"job_tags": ["foo", "bar"]},
        ]
        for cls in primitives:
            for env in env_vars:
                with self.subTest(primitive=cls, env=env):
                    options = Options(environment=env)
                    inst = cls(session=session, options=options)
                    inst.run(self.qx, observables=self.obs)
                    if sys.version_info >= (3, 8):
                        run_options = session.run.call_args.kwargs["options"]
                    else:
                        _, kwargs = session.run.call_args
                        run_options = kwargs["options"]
                    for key, val in env.items():
                        self.assertEqual(run_options[key], val)

    def test_options_copied(self):
        """Test modifying original options does not affect primitives."""
        options = Options()
        primitives = [Sampler, Estimator]
        for cls in primitives:
            with self.subTest(primitive=cls):
                options.transpilation.skip_transpilation = True
                inst = cls(session=MagicMock(spec=MockSession), options=options)
                options.transpilation.skip_transpilation = False
                self.assertTrue(
                    inst.options.get("transpilation").get("skip_transpilation")
                )

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
                    session.close()
                self.assertFalse(session._active)

    def test_run_default_options(self):
        """Test run using default options."""
        session = MagicMock(spec=MockSession)
        options_vars = [
            (Options(resilience_level=9), {"resilience_settings": {"level": 9}}),
            (
                Options(optimization_level=8),
                {"transpilation_settings": {"optimization_settings": {"level": 8}}},
            ),
            (
                {
                    "transpilation": {"initial_layout": [1, 2]},
                    "execution": {"shots": 100},
                },
                {
                    "transpilation_settings": {"initial_layout": [1, 2]},
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
                    self._assert_dict_partially_equal(inputs, expected)

    def test_run_updated_default_options(self):
        """Test run using updated default options."""
        session = MagicMock(spec=MockSession)
        primitives = [Sampler, Estimator]
        for cls in primitives:
            with self.subTest(primitive=cls):
                inst = cls(session=session)
                inst.set_options(resilience_level=1, optimization_level=2, shots=99)
                inst.run(self.qx, observables=self.obs)
                if sys.version_info >= (3, 8):
                    inputs = session.run.call_args.kwargs["inputs"]
                else:
                    _, kwargs = session.run.call_args
                    inputs = kwargs["inputs"]
                self._assert_dict_partially_equal(
                    inputs,
                    {
                        "resilience_settings": {"level": 1},
                        "transpilation_settings": {
                            "optimization_settings": {"level": 2}
                        },
                        "run_options": {"shots": 99},
                    },
                )

    def test_run_overwrite_options(self):
        """Test run using overwritten options."""
        session = MagicMock(spec=MockSession)
        options_vars = [
            ({"resilience_level": 9}, {"resilience_settings": {"level": 9}}),
            ({"shots": 200}, {"run_options": {"shots": 200}}),
            (
                {"optimization_level": 8},
                {"transpilation_settings": {"optimization_settings": {"level": 8}}},
            ),
            (
                {"initial_layout": [1, 2], "optimization_level": 8},
                {
                    "transpilation_settings": {
                        "optimization_settings": {"level": 8},
                        "initial_layout": [1, 2],
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
                    self._assert_dict_partially_equal(inputs, expected)
                    expected = asdict(Options(optimization_level=1, resilience_level=0))
                    self.assertDictEqual(inst.options.__dict__, expected)

    def test_run_overwrite_runtime_options(self):
        """Test run using overwritten runtime options."""
        session = MagicMock(spec=MockSession)
        options_vars = [
            {"log_level": "DEBUG"},
            {"job_tags": ["foo", "bar"]},
            {"max_execution_time": 600},
            {"log_level": "INFO", "max_execution_time": 800},
        ]
        primitives = [Sampler, Estimator]
        for cls in primitives:
            for options in options_vars:
                with self.subTest(primitive=cls, options=options):
                    inst = cls(session=session)
                    inst.run(self.qx, observables=self.obs, **options)
                    if sys.version_info >= (3, 8):
                        rt_options = session.run.call_args.kwargs["options"]
                    else:
                        _, kwargs = session.run.call_args
                        rt_options = kwargs["options"]
                    self._assert_dict_partially_equal(rt_options, options)

    def test_kwarg_options(self):
        """Test specifying arbitrary options."""
        session = MagicMock(spec=MockSession)
        primitives = [Sampler, Estimator]
        for cls in primitives:
            with self.subTest(primitive=cls):
                options = Options(foo="foo")  # pylint: disable=unexpected-keyword-arg
                inst = cls(session=session, options=options)
                inst.run(self.qx, observables=self.obs)
                if sys.version_info >= (3, 8):
                    inputs = session.run.call_args.kwargs["inputs"]
                else:
                    _, kwargs = session.run.call_args
                    inputs = kwargs["inputs"]
                self.assertEqual(inputs.get("foo"), "foo")

    def test_run_kwarg_options(self):
        """Test specifying arbitrary options in run."""
        session = MagicMock(spec=MockSession)
        primitives = [Sampler, Estimator]
        for cls in primitives:
            with self.subTest(primitive=cls):
                inst = cls(session=session)
                inst.run(self.qx, observables=self.obs, foo="foo")
                if sys.version_info >= (3, 8):
                    inputs = session.run.call_args.kwargs["inputs"]
                else:
                    _, kwargs = session.run.call_args
                    inputs = kwargs["inputs"]
                self.assertEqual(inputs.get("foo"), "foo")

    def test_run_multiple_different_options(self):
        """Test multiple runs with different options."""
        session = MagicMock(spec=MockSession)
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
                expected = asdict(Options(optimization_level=1, resilience_level=0))
                self.assertDictEqual(inst.options.__dict__, expected)

    def test_run_same_session(self):
        """Test multiple runs within a session."""
        num_runs = 5
        primitives = [Sampler, Estimator]
        session = MagicMock(spec=MockSession)
        for idx in range(num_runs):
            cls = primitives[idx % 2]
            inst = cls(session=session)
            inst.run(self.qx, observables=self.obs)
        self.assertEqual(session.run.call_count, num_runs)

    @unittest.skip("Skip until data caching is reenabled.")
    def test_primitives_circuit_caching(self):
        """Test circuit caching in Estimator and Sampler classes"""
        psi1 = RealAmplitudes(num_qubits=2, reps=2)
        psi1.measure_all()
        psi2 = RealAmplitudes(num_qubits=2, reps=3)
        psi2.measure_all()
        psi3 = RealAmplitudes(num_qubits=2, reps=2)
        psi3.measure_all()
        psi4 = RealAmplitudes(num_qubits=2, reps=3)
        psi4.measure_all()
        psi1_id = _hash(json.dumps(_circuit_key(psi1), cls=RuntimeEncoder))
        psi2_id = _hash(json.dumps(_circuit_key(psi2), cls=RuntimeEncoder))
        psi3_id = _hash(json.dumps(_circuit_key(psi3), cls=RuntimeEncoder))
        psi4_id = _hash(json.dumps(_circuit_key(psi4), cls=RuntimeEncoder))

        # pylint: disable=invalid-name
        H1 = SparsePauliOp.from_list([("II", 1), ("IZ", 2), ("XI", 3)])
        H2 = SparsePauliOp.from_list([("IZ", 1)])

        with Session(
            service=FakeRuntimeService(channel="ibm_quantum", token="abc"),
            backend="ibmq_qasm_simulator",
        ) as session:
            estimator = Estimator(session=session)

            # calculate [ <psi1(theta1)|H1|psi1(theta1)> ]
            with patch.object(estimator._session, "run") as mock_run:
                estimator.run([psi1, psi2], [H1, H2], [[1] * 6, [1] * 8])
                _, kwargs = mock_run.call_args
                inputs = kwargs["inputs"]
                self.assertDictEqual(inputs["circuits"], {psi1_id: psi1, psi2_id: psi2})
                self.assertEqual(inputs["circuit_ids"], [psi1_id, psi2_id])

            sampler = Sampler(session=session)
            with patch.object(sampler._session, "run") as mock_run:
                sampler.run([psi1, psi2], [[1] * 6, [1] * 8])
                _, kwargs = mock_run.call_args
                inputs = kwargs["inputs"]
                self.assertDictEqual(inputs["circuits"], {})
                self.assertEqual(inputs["circuit_ids"], [psi1_id, psi2_id])

            with patch.object(estimator._session, "run") as mock_run:
                estimator.run([psi3], [H1], [[1] * 6])
                _, kwargs = mock_run.call_args
                inputs = kwargs["inputs"]
                self.assertDictEqual(inputs["circuits"], {psi3_id: psi3})
                self.assertEqual(inputs["circuit_ids"], [psi3_id])

            with patch.object(sampler._session, "run") as mock_run:
                sampler.run([psi4, psi1], [[1] * 8, [1] * 6])
                _, kwargs = mock_run.call_args
                inputs = kwargs["inputs"]
                self.assertDictEqual(inputs["circuits"], {psi4_id: psi4})
                self.assertEqual(inputs["circuit_ids"], [psi4_id, psi1_id])

    def test_set_options(self):
        """Test set options."""
        options = Options(optimization_level=1, execution={"shots": 100})
        new_options = [
            ({"optimization_level": 2}, Options()),
            ({"optimization_level": 3, "shots": 200}, Options()),
            (
                {"shots": 300, "foo": "foo"},
                Options(foo="foo"),  # pylint: disable=unexpected-keyword-arg
            ),
        ]

        session = MagicMock(spec=MockSession)
        primitives = [Sampler, Estimator]
        for cls in primitives:
            for new_opt, new_str in new_options:
                with self.subTest(primitive=cls, new_opt=new_opt):
                    inst = cls(session=session, options=options)
                    inst.set_options(**new_opt)
                    # Make sure the values are equal.
                    inst_options = inst.options.__dict__
                    self.assertTrue(
                        flat_dict_partially_equal(inst_options, new_opt),
                        f"inst_options={inst_options}, new_opt={new_opt}",
                    )
                    # Make sure the structure didn't change.
                    self.assertTrue(
                        dict_keys_equal(inst_options, asdict(new_str)),
                        f"inst_options={inst_options}, new_str={new_str}",
                    )

    def _update_dict(self, dict1, dict2):
        for key, val in dict1.items():
            if isinstance(val, dict):
                self._update_dict(val, dict2.pop(key, {}))
            elif key in dict2.keys():
                dict1[key] = dict2.pop(key)

    def _assert_dict_partially_equal(self, dict1, dict2):
        """Assert all keys in dict2 are in dict1 and have same values."""
        self.assertTrue(
            dict_paritally_equal(dict1, dict2),
            f"{dict1} and {dict2} not partially equal.",
        )
