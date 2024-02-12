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
import os
from unittest.mock import MagicMock, patch
from dataclasses import asdict
from typing import Dict

from qiskit import transpile
from qiskit.circuit import QuantumCircuit

from qiskit.quantum_info import SparsePauliOp
from qiskit_ibm_runtime.fake_provider import FakeManila

from qiskit_ibm_runtime import (
    Sampler,
    Estimator,
    Options,
    Session,
)
from qiskit_ibm_runtime.ibm_backend import IBMBackend
from qiskit_ibm_runtime.utils.default_session import _DEFAULT_SESSION

from ..ibm_test_case import IBMTestCase
from ..utils import (
    dict_paritally_equal,
    flat_dict_partially_equal,
    dict_keys_equal,
    create_faulty_backend,
    bell,
)


class MockSession(Session):
    """Mock for session class"""

    _circuits_map: Dict[str, QuantumCircuit] = {}
    _instance = None


class TestPrimitives(IBMTestCase):
    """Class for testing the Sampler and Estimator classes."""

    @classmethod
    def setUpClass(cls):
        cls.qx = bell()
        cls.obs = SparsePauliOp.from_list([("IZ", 1)])
        return super().setUpClass()

    def tearDown(self) -> None:
        super().tearDown()
        _DEFAULT_SESSION.set(None)

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
                    self.assertDictEqual(expected, inst.options.__dict__)

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
                self.assertTrue(inst.options.get("transpilation").get("skip_transpilation"))

    def test_init_with_backend_str(self):
        """Test initializing a primitive with a backend name."""
        primitives = [Sampler, Estimator]
        backend_name = "ibm_gotham"

        for cls in primitives:
            with self.subTest(primitive=cls), patch(
                "qiskit_ibm_runtime.base_primitive.QiskitRuntimeService"
            ) as mock_service:
                mock_service.reset_mock()
                mock_service_inst = MagicMock()
                mock_service.return_value = mock_service_inst
                mock_backend = MagicMock()
                mock_backend.name = backend_name
                mock_service.global_service = None
                mock_service_inst.backend.return_value = mock_backend

                inst = cls(backend=backend_name)
                mock_service.assert_called_once()
                self.assertIsNone(inst.session)
                inst.run(self.qx, observables=self.obs)
                mock_service_inst.run.assert_called_once()
                runtime_options = mock_service_inst.run.call_args.kwargs["options"]
                self.assertEqual(runtime_options["backend"], backend_name)

    def test_init_with_session_backend_str(self):
        """Test initializing a primitive with a backend name using session."""
        primitives = [Sampler, Estimator]
        backend_name = "ibm_gotham"

        for cls in primitives:
            with self.subTest(primitive=cls), patch(
                "qiskit_ibm_runtime.base_primitive.QiskitRuntimeService"
            ):
                with self.assertRaises(ValueError) as exc:
                    inst = cls(session=backend_name)
                    self.assertIsNone(inst.session)
                self.assertIn("session must be of type Session or None", str(exc.exception))

    def test_init_with_backend_instance(self):
        """Test initializing a primitive with a backend instance."""
        primitives = [Sampler, Estimator]
        service = MagicMock()
        model_backend = FakeManila()
        backend = IBMBackend(
            configuration=model_backend.configuration(), service=service, api_client=MagicMock()
        )
        backend.name = "ibm_gotham"

        for cls in primitives:
            with self.subTest(primitive=cls):
                service.reset_mock()
                inst = cls(backend=backend)
                self.assertIsNone(inst.session)
                inst.run(self.qx, observables=self.obs)
                service.run.assert_called_once()
                runtime_options = service.run.call_args.kwargs["options"]
                self.assertEqual(runtime_options["backend"], backend.name)

                with self.assertRaises(ValueError) as exc:
                    inst = cls(session=backend)
                    self.assertIsNone(inst.session)
                self.assertIn("session must be of type Session or None", str(exc.exception))

    def test_init_with_backend_session(self):
        """Test initializing a primitive with both backend and session."""
        primitives = [Sampler, Estimator]
        session = MagicMock(spec=MockSession)
        backend_name = "ibm_gotham"

        for cls in primitives:
            with self.subTest(primitive=cls):
                session.reset_mock()
                inst = cls(session=session, backend=backend_name)
                self.assertIsNotNone(inst.session)
                inst.run(self.qx, observables=self.obs)
                session.run.assert_called_once()

    def test_init_with_no_backend_session_cloud(self):
        """Test initializing a primitive without backend or session for cloud channel."""
        primitives = [Sampler, Estimator]

        for cls in primitives:
            with self.subTest(primitive=cls), patch(
                "qiskit_ibm_runtime.base_primitive.QiskitRuntimeService"
            ) as mock_service:
                mock_service_inst = MagicMock()
                mock_service_inst.channel = "ibm_cloud"
                mock_service.return_value = mock_service_inst
                mock_service.reset_mock()
                mock_service.global_service = None
                inst = cls()
                mock_service.assert_called_once()
                self.assertIsNone(inst.session)

    def test_init_with_no_backend_session_quantum(self):
        """Test initializing a primitive without backend or session for quantum channel."""
        primitives = [Sampler, Estimator]

        for cls in primitives:
            with self.subTest(primitive=cls), patch(
                "qiskit_ibm_runtime.base_primitive.QiskitRuntimeService"
            ) as mock_service:
                mock_service.reset_mock()
                with self.assertRaises(ValueError):
                    _ = cls()

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
        cm_backend = "ibm_metropolis"
        primitives = [Sampler, Estimator]
        model_backend = FakeManila()
        for cls in primitives:
            with self.subTest(primitive=cls):
                service = MagicMock()
                backend = IBMBackend(
                    configuration=model_backend.configuration(),
                    service=service,
                    api_client=MagicMock(),
                )
                backend.name = "ibm_gotham"

                with Session(service=service, backend=cm_backend):
                    inst = cls(backend=backend)
                    self.assertIsNone(inst.session)
                    inst.run(self.qx, observables=self.obs)
                    service.run.assert_called_once()
                    runtime_options = service.run.call_args.kwargs["options"]
                    self.assertEqual(runtime_options["backend"], backend.name)

    def test_no_session(self):
        """Test running without session."""
        primitives = [Sampler, Estimator]
        model_backend = FakeManila()
        for cls in primitives:
            with self.subTest(primitive=cls):
                service = MagicMock()
                backend = IBMBackend(
                    configuration=model_backend.configuration(),
                    service=service,
                    api_client=MagicMock(),
                )
                inst = cls(backend)
                inst.run(self.qx, observables=self.obs)
                self.assertIsNone(inst.session)
                service.run.assert_called_once()
                kwargs_list = service.run.call_args.kwargs
                self.assertNotIn("session_id", kwargs_list)
                self.assertNotIn("start_session", kwargs_list)

    def test_run_default_options(self):
        """Test run using default options."""
        session = MagicMock(spec=MockSession)
        options_vars = [
            (Options(resilience_level=1), {"resilience_settings": {"level": 1}}),
            (
                Options(optimization_level=3),
                {"transpilation_settings": {"optimization_settings": {"level": 3}}},
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
                        "transpilation_settings": {"optimization_settings": {"level": 2}},
                        "run_options": {"shots": 99},
                    },
                )

    def test_run_overwrite_options(self):
        """Test run using overwritten options."""
        session = MagicMock(spec=MockSession)
        options_vars = [
            ({"resilience_level": 1}, {"resilience_settings": {"level": 1}}),
            ({"shots": 200}, {"run_options": {"shots": 200}}),
            (
                {"optimization_level": 3},
                {"transpilation_settings": {"optimization_settings": {"level": 3}}},
            ),
            (
                {"initial_layout": [1, 2], "optimization_level": 2},
                {
                    "transpilation_settings": {
                        "optimization_settings": {"level": 2},
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
                    self.assertDictEqual(inst.options.__dict__, asdict(Options()))

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
                    self.assertEqual(kwargs_list[idx][1]["inputs"]["run_options"]["shots"], shots)
                self.assertDictEqual(inst.options.__dict__, asdict(Options()))

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

    def test_set_options(self):
        """Test set options."""
        options = Options(optimization_level=1, execution={"shots": 100})
        new_options = [
            ({"optimization_level": 2}, Options()),
            ({"optimization_level": 3, "shots": 200}, Options()),
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

    def test_accept_level_1_options(self):
        """Test initializing options properly when given on level 1."""

        options_dicts = [
            {},
            {"shots": 10},
            {"seed_simulator": 123},
            {"skip_transpilation": True, "log_level": "ERROR"},
            {"initial_layout": [1, 2], "shots": 100, "noise_factors": (0, 2, 4)},
        ]

        expected_list = [Options(), Options(), Options(), Options(), Options()]
        expected_list[1].execution.shots = 10
        expected_list[2].simulator.seed_simulator = 123
        expected_list[3].transpilation.skip_transpilation = True
        expected_list[3].environment.log_level = "ERROR"
        expected_list[4].transpilation.initial_layout = [1, 2]
        expected_list[4].execution.shots = 100
        expected_list[4].resilience.noise_factors = (0, 2, 4)

        session = MagicMock(spec=MockSession)
        primitives = [Sampler, Estimator]
        for cls in primitives:
            for opts, expected in zip(options_dicts, expected_list):
                with self.subTest(primitive=cls, options=opts):
                    inst1 = cls(session=session, options=opts)
                    inst2 = cls(session=session, options=expected)
                    # Make sure the values are equal.
                    inst1_options = inst1.options.__dict__
                    expected_dict = inst2.options.__dict__
                    self.assertTrue(
                        dict_paritally_equal(inst1_options, expected_dict),
                        f"inst_options={inst1_options}, options={opts}",
                    )
                    # Make sure the structure didn't change.
                    self.assertTrue(
                        dict_keys_equal(inst1_options, expected_dict),
                        f"inst_options={inst1_options}, expected={expected_dict}",
                    )

    def test_default_error_levels(self):
        """Test the correct default error levels are used."""

        session = MagicMock(spec=MockSession)
        primitives = [Sampler, Estimator]
        for cls in primitives:
            with self.subTest(primitive=cls):
                options = Options(
                    simulator={"noise_model": "foo"},
                )
                inst = cls(session=session, options=options)

                if isinstance(inst, Estimator):
                    inst.run(self.qx, observables=self.obs)
                else:
                    inst.run(self.qx)

                if sys.version_info >= (3, 8):
                    inputs = session.run.call_args.kwargs["inputs"]
                else:
                    _, kwargs = session.run.call_args
                    inputs = kwargs["inputs"]
                self.assertEqual(
                    inputs["transpilation_settings"]["optimization_settings"]["level"],
                    Options._DEFAULT_OPTIMIZATION_LEVEL,
                )
                self.assertEqual(
                    inputs["resilience_settings"]["level"],
                    Options._DEFAULT_RESILIENCE_LEVEL,
                )

                session.service.backend().configuration().simulator = False
                inst = cls(session=session)
                inst.run(self.qx, observables=self.obs)
                if sys.version_info >= (3, 8):
                    inputs = session.run.call_args.kwargs["inputs"]
                else:
                    _, kwargs = session.run.call_args
                    inputs = kwargs["inputs"]
                self.assertEqual(
                    inputs["transpilation_settings"]["optimization_settings"]["level"],
                    Options._DEFAULT_OPTIMIZATION_LEVEL,
                )
                self.assertEqual(
                    inputs["resilience_settings"]["level"],
                    Options._DEFAULT_RESILIENCE_LEVEL,
                )

                session.service.backend().configuration().simulator = True
                inst = cls(session=session)
                inst.run(self.qx, observables=self.obs)
                if sys.version_info >= (3, 8):
                    inputs = session.run.call_args.kwargs["inputs"]
                else:
                    _, kwargs = session.run.call_args
                    inputs = kwargs["inputs"]
                self.assertEqual(
                    inputs["transpilation_settings"]["optimization_settings"]["level"],
                    1,
                )
                self.assertEqual(inputs["resilience_settings"]["level"], 0)

    def test_resilience_options(self):
        """Test resilience options."""
        options_dicts = [
            {"resilience": {"extrapolator": "NoExtrapolator"}},
            {
                "resilience": {
                    "extrapolator": "QuarticExtrapolator",
                    "noise_factors": [1, 2, 3, 4],
                },
            },
            {
                "resilience": {
                    "extrapolator": "CubicExtrapolator",
                    "noise_factors": [1, 2, 3],
                },
            },
        ]
        session = MagicMock(spec=MockSession)
        primitives = [Sampler, Estimator]

        for cls in primitives:
            for opts_dict in options_dicts:
                # When this environment variable is set, validation is turned off
                try:
                    os.environ["QISKIT_RUNTIME_SKIP_OPTIONS_VALIDATION"] = "1"
                    inst = cls(session=session, options=opts_dict)
                    inst.run(self.qx, observables=self.obs)
                finally:
                    # Delete environment variable to validate input
                    del os.environ["QISKIT_RUNTIME_SKIP_OPTIONS_VALIDATION"]
                with self.assertRaises(ValueError) as exc:
                    inst = cls(session=session, options=opts_dict)
                    inst.run(self.qx, observables=self.obs)
                self.assertIn(list(opts_dict["resilience"].values())[0], str(exc.exception))
                if len(opts_dict["resilience"].keys()) > 1:
                    self.assertIn(list(opts_dict["resilience"].keys())[1], str(exc.exception))

    def test_environment_options(self):
        """Test environment options."""
        options_dicts = [
            {"environment": {"log_level": "NoLogLevel"}},
        ]
        session = MagicMock(spec=MockSession)
        primitives = [Sampler, Estimator]

        for cls in primitives:
            for opts_dict in options_dicts:
                # When this environment variable is set, validation is turned off
                try:
                    os.environ["QISKIT_RUNTIME_SKIP_OPTIONS_VALIDATION"] = "1"
                    inst = cls(session=session, options=opts_dict)
                    inst.run(self.qx, observables=self.obs)
                finally:
                    # Delete environment variable to validate input
                    del os.environ["QISKIT_RUNTIME_SKIP_OPTIONS_VALIDATION"]
                with self.assertRaises(ValueError) as exc:
                    inst = cls(session=session, options=opts_dict)
                    inst.run(self.qx, observables=self.obs)
                self.assertIn(list(opts_dict["environment"].values())[0], str(exc.exception))

    def test_transpilation_options(self):
        """Test transpilation options."""
        options_dicts = [
            {"transpilation": {"layout_method": "NoLayoutMethod"}},
            {"transpilation": {"routing_method": "NoRoutingMethod"}},
            {"transpilation": {"approximation_degree": 1.1}},
        ]
        session = MagicMock(spec=MockSession)
        primitives = [Sampler, Estimator]

        for cls in primitives:
            for opts_dict in options_dicts:
                # When this environment variable is set, validation is turned off
                try:
                    os.environ["QISKIT_RUNTIME_SKIP_OPTIONS_VALIDATION"] = "1"
                    inst = cls(session=session, options=opts_dict)
                    inst.run(self.qx, observables=self.obs)
                finally:
                    # Delete environment variable to validate input
                    del os.environ["QISKIT_RUNTIME_SKIP_OPTIONS_VALIDATION"]
                with self.assertRaises(ValueError) as exc:
                    inst = cls(session=session, options=opts_dict)
                    inst.run(self.qx, observables=self.obs)
                self.assertIn(list(opts_dict["transpilation"].keys())[0], str(exc.exception))

    def test_max_execution_time_options(self):
        """Test transpilation options."""
        options_dicts = [
            {"max_execution_time": Options._MAX_EXECUTION_TIME + 1},
        ]
        session = MagicMock(spec=MockSession)
        primitives = [Sampler, Estimator]

        for cls in primitives:
            for opts_dict in options_dicts:
                # When this environment variable is set, validation is turned off
                try:
                    os.environ["QISKIT_RUNTIME_SKIP_OPTIONS_VALIDATION"] = "1"
                    inst = cls(session=session, options=opts_dict)
                    inst.run(self.qx, observables=self.obs)
                finally:
                    # Delete environment variable to validate input
                    del os.environ["QISKIT_RUNTIME_SKIP_OPTIONS_VALIDATION"]
                with self.assertRaises(ValueError) as exc:
                    inst = cls(session=session, options=opts_dict)
                    inst.run(self.qx, observables=self.obs)
                self.assertIn(
                    "max_execution_time must be below 28800 seconds",
                    str(exc.exception),
                )

    def test_raise_faulty_qubits(self):
        """Test faulty qubits is raised."""
        fake_backend = FakeManila()
        num_qubits = fake_backend.configuration().num_qubits
        circ = QuantumCircuit(num_qubits, num_qubits)
        for i in range(num_qubits):
            circ.x(i)
        transpiled = transpile(circ, backend=fake_backend)
        observable = SparsePauliOp("Z" * num_qubits)

        faulty_qubit = 4
        ibm_backend = create_faulty_backend(fake_backend, faulty_qubit=faulty_qubit)
        service = MagicMock()
        service.backend.return_value = ibm_backend
        session = Session(service=service, backend=fake_backend.name)
        sampler = Sampler(session=session)
        estimator = Estimator(session=session)

        with self.assertRaises(ValueError) as err:
            estimator.run(transpiled, observable, skip_transpilation=True)
        self.assertIn(f"faulty qubit {faulty_qubit}", str(err.exception))

        transpiled.measure_all()
        with self.assertRaises(ValueError) as err:
            sampler.run(transpiled, skip_transpilation=True)
        self.assertIn(f"faulty qubit {faulty_qubit}", str(err.exception))

    def test_raise_faulty_qubits_many(self):
        """Test faulty qubits is raised if one circuit uses it."""
        fake_backend = FakeManila()
        num_qubits = fake_backend.configuration().num_qubits

        circ1 = QuantumCircuit(1, 1)
        circ1.x(0)
        circ2 = QuantumCircuit(num_qubits, num_qubits)
        for i in range(num_qubits):
            circ2.x(i)
        transpiled = transpile([circ1, circ2], backend=fake_backend)
        observable = SparsePauliOp("Z" * num_qubits)

        faulty_qubit = 4
        ibm_backend = create_faulty_backend(fake_backend, faulty_qubit=faulty_qubit)
        service = MagicMock()
        service.backend.return_value = ibm_backend
        session = Session(service=service, backend=fake_backend.name)
        sampler = Sampler(session=session)
        estimator = Estimator(session=session)

        with self.assertRaises(ValueError) as err:
            estimator.run(transpiled, [observable, observable], skip_transpilation=True)
        self.assertIn(f"faulty qubit {faulty_qubit}", str(err.exception))

        for circ in transpiled:
            circ.measure_all()

        with self.assertRaises(ValueError) as err:
            sampler.run(transpiled, skip_transpilation=True)
        self.assertIn(f"faulty qubit {faulty_qubit}", str(err.exception))

    def test_raise_faulty_edge(self):
        """Test faulty edge is raised."""
        fake_backend = FakeManila()
        num_qubits = fake_backend.configuration().num_qubits
        circ = QuantumCircuit(num_qubits, num_qubits)
        for i in range(num_qubits - 2):
            circ.cx(i, i + 1)
        transpiled = transpile(circ, backend=fake_backend)
        observable = SparsePauliOp("Z" * num_qubits)

        edge_qubits = [0, 1]
        ibm_backend = create_faulty_backend(fake_backend, faulty_edge=("cx", edge_qubits))
        service = MagicMock()
        service.backend.return_value = ibm_backend
        session = Session(service=service, backend=fake_backend.name)
        sampler = Sampler(session=session)
        estimator = Estimator(session=session)

        with self.assertRaises(ValueError) as err:
            estimator.run(transpiled, observable, skip_transpilation=True)
        self.assertIn("cx", str(err.exception))
        self.assertIn(f"faulty edge {tuple(edge_qubits)}", str(err.exception))

        transpiled.measure_all()
        with self.assertRaises(ValueError) as err:
            sampler.run(transpiled, skip_transpilation=True)
        self.assertIn("cx", str(err.exception))
        self.assertIn(f"faulty edge {tuple(edge_qubits)}", str(err.exception))

    def test_faulty_qubit_not_used(self):
        """Test faulty qubit is not raise if not used."""
        fake_backend = FakeManila()
        circ = QuantumCircuit(2, 2)
        for i in range(2):
            circ.x(i)
        transpiled = transpile(circ, backend=fake_backend, initial_layout=[0, 1])
        observable = SparsePauliOp("Z" * fake_backend.configuration().num_qubits)

        faulty_qubit = 4
        ibm_backend = create_faulty_backend(fake_backend, faulty_qubit=faulty_qubit)

        service = MagicMock()
        service.backend.return_value = ibm_backend
        session = Session(service=service, backend=fake_backend.name)
        sampler = Sampler(session=session)
        estimator = Estimator(session=session)

        with patch.object(Session, "run") as mock_run:
            estimator.run(transpiled, observable, skip_transpilation=True)
        mock_run.assert_called_once()

        transpiled.measure_active()
        with patch.object(Session, "run") as mock_run:
            sampler.run(transpiled, skip_transpilation=True)
        mock_run.assert_called_once()

    def test_faulty_edge_not_used(self):
        """Test faulty edge is not raised if not used."""
        fake_backend = FakeManila()
        coupling_map = fake_backend.configuration().coupling_map

        circ = QuantumCircuit(2, 2)
        circ.cx(0, 1)

        transpiled = transpile(circ, backend=fake_backend, initial_layout=coupling_map[0])
        observable = SparsePauliOp("Z" * fake_backend.configuration().num_qubits)

        edge_qubits = coupling_map[-1]
        ibm_backend = create_faulty_backend(fake_backend, faulty_edge=("cx", edge_qubits))

        service = MagicMock()
        service.backend.return_value = ibm_backend
        session = Session(service=service, backend=fake_backend.name)
        sampler = Sampler(session=session)
        estimator = Estimator(session=session)

        with patch.object(Session, "run") as mock_run:
            estimator.run(transpiled, observable, skip_transpilation=True)
        mock_run.assert_called_once()

        transpiled.measure_all()
        with patch.object(Session, "run") as mock_run:
            sampler.run(transpiled, skip_transpilation=True)
        mock_run.assert_called_once()

    def test_no_raise_skip_transpilation(self):
        """Test faulty qubits and edges are not raise if not skipping."""
        fake_backend = FakeManila()
        num_qubits = fake_backend.configuration().num_qubits
        circ = QuantumCircuit(num_qubits, num_qubits)
        for i in range(num_qubits - 2):
            circ.cx(i, i + 1)
        transpiled = transpile(circ, backend=fake_backend)
        observable = SparsePauliOp("Z" * num_qubits)

        edge_qubits = [0, 1]
        ibm_backend = create_faulty_backend(
            fake_backend, faulty_qubit=0, faulty_edge=("cx", edge_qubits)
        )

        service = MagicMock()
        service.backend.return_value = ibm_backend
        session = Session(service=service, backend=fake_backend.name)
        sampler = Sampler(session=session)
        estimator = Estimator(session=session)

        with patch.object(Session, "run") as mock_run:
            estimator.run(transpiled, observable)
        mock_run.assert_called_once()

        transpiled.measure_all()
        with patch.object(Session, "run") as mock_run:
            sampler.run(transpiled)
        mock_run.assert_called_once()

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

    def test_qctrl_supported_values_for_options(self):
        """Test exception when options levels not supported."""
        no_resilience_options = {
            "noise_factors": None,
            "extrapolator": None,
        }

        options_good = [
            # Minium working settings
            {},
            # No warnings, we need resilience options here because by default they are getting populated.
            {"resilience": no_resilience_options},
            # Arbitrary approximation degree (issues warning)
            {"approximation_degree": 1},
            # Arbitrary resilience options(issue warning)
            {
                "resilience_level": 1,
                "resilience": {"noise_factors": (1, 1, 3)},
                "approximation_degree": 1,
            },
            # Resilience level > 1 (issue warning)
            {"resilience_level": 2},
            # Optimization level = 1,2 (issue warning)
            {"optimization_level": 1},
            {"optimization_level": 2},
            # Skip transpilation level(issue warning)
            {"skip_transpilation": True},
        ]
        session = MagicMock(spec=MockSession)
        session.service._channel_strategy = "q-ctrl"
        session.service.backend().configuration().simulator = False
        primitives = [Sampler, Estimator]
        for cls in primitives:
            for options in options_good:
                with self.subTest(msg=f"{cls}, {options}"):
                    inst = cls(session=session)
                    if isinstance(inst, Estimator):
                        _ = inst.run(self.qx, observables=self.obs, **options)
                    else:
                        _ = inst.run(self.qx, **options)

    def test_qctrl_unsupported_values_for_options(self):
        """Test exception when options levels are not supported."""
        options_bad = [
            # Bad resilience levels
            ({"resilience_level": 0}, "resilience level"),
            # Bad optimization level
            ({"optimization_level": 0}, "optimization level"),
        ]
        session = MagicMock(spec=MockSession)
        session.service._channel_strategy = "q-ctrl"
        session.service.backend().configuration().simulator = False
        primitives = [Sampler, Estimator]
        for cls in primitives:
            for bad_opt, expected_message in options_bad:
                with self.subTest(msg=bad_opt):
                    inst = cls(session=session)
                    with self.assertRaises(ValueError) as exc:
                        if isinstance(inst, Sampler):
                            _ = inst.run(self.qx, **bad_opt)
                        else:
                            _ = inst.run(self.qx, observables=self.obs, **bad_opt)

                        self.assertIn(expected_message, str(exc.exception))
