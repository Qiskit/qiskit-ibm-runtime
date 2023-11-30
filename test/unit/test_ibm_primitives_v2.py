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
from dataclasses import asdict
from unittest import skip
from unittest.mock import MagicMock, patch

from ddt import data, ddt
import numpy as np

from qiskit import transpile
from qiskit.circuit import QuantumCircuit
from qiskit.circuit.library import RealAmplitudes
from qiskit.test.reference_circuits import ReferenceCircuits
from qiskit.quantum_info import SparsePauliOp
from qiskit.providers.fake_provider import FakeManila

from qiskit_ibm_runtime import (
    Sampler,
    Estimator,
    Options,
    Session,
)
from qiskit_ibm_runtime.ibm_backend import IBMBackend
from qiskit_ibm_runtime.utils.default_session import _DEFAULT_SESSION
from qiskit_ibm_runtime import EstimatorV2
from qiskit_ibm_runtime.estimator import Estimator as IBMBaseEstimator
from qiskit_ibm_runtime.qiskit.primitives import BindingsArray

from ..ibm_test_case import IBMTestCase
from ..utils import (
    dict_paritally_equal,
    flat_dict_partially_equal,
    dict_keys_equal,
    create_faulty_backend,
    combine,
    MockSession,
    get_primitive_inputs,
    get_mocked_backend,
)


# TODO: Add SamplerV2 back when it's supported
@ddt
class TestPrimitivesV2(IBMTestCase):
    """Class for testing the Sampler and Estimator classes."""

    @classmethod
    def setUpClass(cls):
        cls.circ = ReferenceCircuits.bell()
        cls.obs = SparsePauliOp.from_list([("IZ", 1)])
        return super().setUpClass()

    def tearDown(self) -> None:
        super().tearDown()
        _DEFAULT_SESSION.set(None)

    @data(EstimatorV2)
    def test_dict_options(self, primitive):
        """Test passing a dictionary as options."""
        options_vars = [
            {},
            {
                "max_execution_time": 100,
                "transpilation": {"initial_layout": [1, 2]},
                "execution": {"shots": 100, "init_qubits": True},
            },
            {"optimization_level": 2},
            {"transpilation": {}},
        ]
        for options in options_vars:
            inst = primitive(session=MagicMock(spec=MockSession), options=options)
            self.assertTrue(dict_paritally_equal(asdict(inst.options), options))

    @combine(
        primitive=[EstimatorV2],
        env_var=[
            {"log_level": "DEBUG"},
            {"job_tags": ["foo", "bar"]},
        ],
    )
    def test_runtime_options(self, primitive, env_var):
        """Test RuntimeOptions specified as primitive options."""
        session = MagicMock(spec=MockSession)
        options = primitive._options_class(environment=env_var)
        inst = primitive(session=session, options=options)
        inst.run(**get_primitive_inputs(inst))
        run_options = session.run.call_args.kwargs["options"]
        for key, val in env_var.items():
            self.assertEqual(run_options[key], val)

    @combine(
        primitive=[EstimatorV2],
        opts=[
            {"experimental": {"image": "foo:bar"}},
            {"experimental": {"image": "foo:bar"}, "environment": {"log_level": "INFO"}},
        ],
    )
    def test_image(self, primitive, opts):
        """Test passing an image to options."""
        session = MagicMock(spec=MockSession)
        options = primitive._options_class(**opts)
        inst = primitive(session=session, options=options)
        inst.run(**get_primitive_inputs(inst))
        run_options = session.run.call_args.kwargs["options"]
        input_params = session.run.call_args.kwargs["inputs"]
        expected = list(opts.values())[0]
        for key, val in expected.items():
            self.assertEqual(run_options[key], val)
            self.assertNotIn(key, input_params)

    @data(EstimatorV2)
    def test_options_copied(self, primitive):
        """Test modifying original options does not affect primitives."""
        options = primitive._options_class()
        options.max_execution_time = 100
        inst = primitive(session=MagicMock(spec=MockSession), options=options)
        options.max_execution_time = 200
        self.assertEqual(inst.options.max_execution_time, 100)

    @data(EstimatorV2)
    def test_init_with_backend_str(self, primitive):
        """Test initializing a primitive with a backend name."""
        backend_name = "ibm_gotham"

        with patch("qiskit_ibm_runtime.base_primitive.QiskitRuntimeService") as mock_service:
            mock_service.reset_mock()
            mock_service_inst = MagicMock()
            mock_service.return_value = mock_service_inst
            mock_backend = MagicMock()
            mock_backend.name = backend_name
            mock_service.global_service = None
            mock_service_inst.backend.return_value = mock_backend

            inst = primitive(backend=backend_name)
            mock_service.assert_called_once()
            self.assertIsNone(inst.session)
            inst.run(**get_primitive_inputs(inst))
            mock_service_inst.run.assert_called_once()
            runtime_options = mock_service_inst.run.call_args.kwargs["options"]
            self.assertEqual(runtime_options["backend"], backend_name)

    @data(EstimatorV2)
    def test_init_with_session_backend_str(self, primitive):
        """Test initializing a primitive with a backend name using session."""
        backend_name = "ibm_gotham"

        with patch("qiskit_ibm_runtime.base_primitive.QiskitRuntimeService"):
            with self.assertRaises(ValueError) as exc:
                inst = primitive(session=backend_name)
                self.assertIsNone(inst.session)
            self.assertIn("session must be of type Session or None", str(exc.exception))

    @data(EstimatorV2)
    def test_init_with_backend_instance(self, primitive):
        """Test initializing a primitive with a backend instance."""
        service = MagicMock()
        model_backend = FakeManila()
        backend = IBMBackend(
            configuration=model_backend.configuration(), service=service, api_client=MagicMock()
        )
        backend.name = "ibm_gotham"

        service.reset_mock()
        inst = primitive(backend=backend)
        self.assertIsNone(inst.session)
        inst.run(**get_primitive_inputs(inst))
        service.run.assert_called_once()
        runtime_options = service.run.call_args.kwargs["options"]
        self.assertEqual(runtime_options["backend"], backend.name)

        with self.assertRaises(ValueError) as exc:
            inst = primitive(session=backend)
            self.assertIsNone(inst.session)
        self.assertIn("session must be of type Session or None", str(exc.exception))

    @data(EstimatorV2)
    def test_init_with_backend_session(self, primitive):
        """Test initializing a primitive with both backend and session."""
        session = MagicMock(spec=MockSession)
        backend_name = "ibm_gotham"

        session.reset_mock()
        inst = primitive(session=session, backend=backend_name)
        self.assertIsNotNone(inst.session)
        inst.run(**get_primitive_inputs(inst))
        session.run.assert_called_once()

    @data(EstimatorV2)
    def test_init_with_no_backend_session_cloud(self, primitive):
        """Test initializing a primitive without backend or session for cloud channel."""
        with patch("qiskit_ibm_runtime.base_primitive.QiskitRuntimeService") as mock_service:
            mock_service_inst = MagicMock()
            mock_service_inst.channel = "ibm_cloud"
            mock_service.return_value = mock_service_inst
            mock_service.reset_mock()
            mock_service.global_service = None
            inst = primitive()
            mock_service.assert_called_once()
            self.assertIsNone(inst.session)

    @data(EstimatorV2)
    def test_init_with_no_backend_session_quantum(self, primitive):
        """Test initializing a primitive without backend or session for quantum channel."""

        with patch("qiskit_ibm_runtime.base_primitive.QiskitRuntimeService") as mock_service:
            mock_service.reset_mock()
            with self.assertRaises(ValueError):
                _ = primitive()

    @data(EstimatorV2)
    def test_default_session_context_manager(self, primitive):
        """Test getting default session within context manager."""
        service = MagicMock()
        backend = "ibm_gotham"

        with Session(service=service, backend=backend) as session:
            inst = primitive()
            self.assertEqual(inst.session, session)
            self.assertEqual(inst.session.backend(), backend)

    @data(EstimatorV2)
    def test_default_session_cm_new_backend(self, primitive):
        """Test using a different backend within context manager."""
        cm_backend = "ibm_metropolis"
        model_backend = FakeManila()
        service = MagicMock()
        backend = IBMBackend(
            configuration=model_backend.configuration(),
            service=service,
            api_client=MagicMock(),
        )
        backend.name = "ibm_gotham"

        with Session(service=service, backend=cm_backend):
            inst = primitive(backend=backend)
            self.assertIsNone(inst.session)
            inst.run(**get_primitive_inputs(inst))
            service.run.assert_called_once()
            runtime_options = service.run.call_args.kwargs["options"]
            self.assertEqual(runtime_options["backend"], backend.name)

    @data(EstimatorV2)
    def test_no_session(self, primitive):
        """Test running without session."""
        model_backend = FakeManila()
        service = MagicMock()
        backend = IBMBackend(
            configuration=model_backend.configuration(),
            service=service,
            api_client=MagicMock(),
        )
        inst = primitive(backend)
        inst.run(**get_primitive_inputs(inst))
        self.assertIsNone(inst.session)
        service.run.assert_called_once()
        kwargs_list = service.run.call_args.kwargs
        self.assertNotIn("session_id", kwargs_list)
        self.assertNotIn("start_session", kwargs_list)

    @data(EstimatorV2)
    def test_parameters_single_circuit(self, primitive):
        """Test parameters for a single cirucit."""

        circ = RealAmplitudes(num_qubits=2, reps=1)

        param_vals = [
            # 1 set of parameter values
            [1, 2, 3, 4],
            [np.pi] * circ.num_parameters,
            np.random.uniform(size=(4,)),
            # {param: [2.0] for param in circ.parameters},  # TODO: this doesn't work now
            # N sets of parameter values
            # [[1, 2, 3, 4]] * 2,  # TODO: This doesn't work right now
            np.random.random((2, 4)),
            np.linspace(0, 1, 24).reshape((2, 3, 4)),
            {param: [1, 2, 3] for param in circ.parameters},
            {param: np.linspace(0, 1, 5) for param in circ.parameters},
            {tuple(circ.parameters): np.random.random((2, 3, 4))},
            {
                tuple(circ.parameters[:2]): np.random.random((2, 1, 2)),
                tuple(circ.parameters[2:4]): np.random.random((2, 1, 2)),
            },
        ]

        inst = primitive(backend=get_mocked_backend())
        for val in param_vals:
            with self.subTest(val=val):
                pub = (circ, "ZZ", val) if isinstance(inst, EstimatorV2) else (circ, val)
                inst.run(pub)

    @data(EstimatorV2)
    def test_parameters_vals_kwvals(self, primitive):
        """Test a mixture of vals and kwvals."""
        circ = RealAmplitudes(num_qubits=2, reps=1)
        inst = primitive(backend=get_mocked_backend())

        with self.subTest("0-d"):
            param_vals = np.linspace(0, 1, 4)
            kwvals = {tuple(circ.parameters[:2]): param_vals[:2]}
            barray = BindingsArray(vals=param_vals[2:], kwvals=kwvals)
            pub = (circ, "ZZ", barray) if isinstance(inst, EstimatorV2) else (circ, barray)
            inst.run(pub)

        with self.subTest("n-d"):
            kwvals = {tuple(circ.parameters[:2]): np.random.random((2, 3, 2))}
            barray = BindingsArray(vals=np.random.random((2, 3, 2)), kwvals=kwvals)
            pub = (circ, "ZZ", barray) if isinstance(inst, EstimatorV2) else (circ, barray)
            inst.run(pub)

    @data(EstimatorV2)
    def test_parameters_multiple_circuits(self, primitive):
        """Test multiple parameters for multiple circuits."""
        circuits = [
            QuantumCircuit(2),
            RealAmplitudes(num_qubits=2, reps=1),
            RealAmplitudes(num_qubits=3, reps=1),
        ]

        param_vals = [
            (
                [],
                np.random.uniform(size=(4,)),
                np.random.uniform(size=(6,)),
            ),
            (
                [],
                np.random.random((2, 4)),
                np.random.random((2, 6)),
            ),
        ]

        inst = primitive(backend=get_mocked_backend())
        for all_params in param_vals:
            with self.subTest(all_params=all_params):
                pubs = []
                for circ, circ_params in zip(circuits, all_params):
                    publet = (
                        (circ, "Z" * circ.num_qubits, circ_params)
                        if isinstance(inst, EstimatorV2)
                        else (circ, circ_params)
                    )
                    pubs.append(publet)
                inst.run(pubs)

    @data(EstimatorV2)
    def test_run_updated_options(self, primitive):
        """Test run using overwritten options."""
        session = MagicMock(spec=MockSession)
        options_vars = [
            ({"dynamical_decoupling": "XY4"}, {"dynamical_decoupling": "XY4"}),
            ({"shots": 200}, {"execution": {"shots": 200}}),
            (
                {"optimization_level": 3},
                {"transpilation": {"optimization_level": 3}},
            ),
            (
                {"initial_layout": [1, 2], "optimization_level": 2},
                {
                    "transpilation": {
                        "optimization_level": 2,
                        "initial_layout": [1, 2],
                    }
                },
            ),
            (
                {"skip_transpilation": True},
                {"skip_transpilation": True},
            ),
        ]

        for options, expected in options_vars:
            with self.subTest(options=options):
                inst = primitive(session=session)
                inst.options.update(**options)
                inst.run(**get_primitive_inputs(inst))
                inputs = session.run.call_args.kwargs["inputs"]
                self._assert_dict_partially_equal(inputs, expected)

    @data(EstimatorV2)
    def test_run_overwrite_runtime_options(self, primitive):
        """Test run using overwritten runtime options."""
        session = MagicMock(spec=MockSession)
        options_vars = [
            {"log_level": "DEBUG"},
            {"job_tags": ["foo", "bar"]},
            {"max_execution_time": 600},
            {"log_level": "INFO", "max_execution_time": 800},
        ]
        for options in options_vars:
            with self.subTest(options=options):
                inst = primitive(session=session)
                inst.options.update(**options)
                inst.run(**get_primitive_inputs(inst))
                rt_options = session.run.call_args.kwargs["options"]
                self._assert_dict_partially_equal(rt_options, options)

    @combine(
        primitive=[EstimatorV2],
        exp_opt=[{"foo": "bar"}, {"transpilation": {"foo": "bar"}}],
    )
    def test_run_experimental_options(self, primitive, exp_opt):
        """Test specifying arbitrary options in run."""
        session = MagicMock(spec=MockSession)
        inst = primitive(session=session)
        inst.options.experimental = exp_opt
        inst.run(**get_primitive_inputs(inst))
        inputs = session.run.call_args.kwargs["inputs"]
        self._assert_dict_partially_equal(inputs, exp_opt)

    @data(EstimatorV2)
    def test_run_unset_options(self, primitive):
        """Test running with unset options."""
        session = MagicMock(spec=MockSession)
        inst = primitive(session=session)
        inst.run(**get_primitive_inputs(inst))
        inputs = session.run.call_args.kwargs["inputs"]
        for fld in ["pubs", "_experimental"]:
            inputs.pop(fld, None)
        expected = {"skip_transpilation": False, "execution": {"init_qubits": True}, "version": 2}
        self.assertDictEqual(inputs, expected)

    @data(EstimatorV2)
    def test_run_multiple_different_options(self, primitive):
        """Test multiple runs with different options."""
        session = MagicMock(spec=MockSession)
        inst = primitive(session=session, options={"shots": 100})
        inst.run(**get_primitive_inputs(inst))
        inst.options.update(shots=200)
        inst.run(**get_primitive_inputs(inst))
        kwargs_list = session.run.call_args_list
        for idx, shots in zip([0, 1], [100, 200]):
            self.assertEqual(kwargs_list[idx][1]["inputs"]["execution"]["shots"], shots)

    def test_run_same_session(self):
        """Test multiple runs within a session."""
        num_runs = 5
        primitives = [EstimatorV2]
        session = MagicMock(spec=MockSession)
        for idx in range(num_runs):
            cls = primitives[idx % len(primitives)]
            inst = cls(session=session)
            inst.run(**get_primitive_inputs(inst))
        self.assertEqual(session.run.call_count, num_runs)

    @combine(
        primitive=[EstimatorV2],
        new_opts=[
            {"optimization_level": 2},
            {"optimization_level": 3, "shots": 200},
        ],
    )
    def test_set_options(self, primitive, new_opts):
        """Test set options."""
        opt_cls = primitive._options_class
        options = opt_cls(optimization_level=1, execution={"shots": 100})

        session = MagicMock(spec=MockSession)
        inst = primitive(session=session, options=options)
        inst.options.update(**new_opts)
        # Make sure the values are equal.
        inst_options = asdict(inst.options)
        self.assertTrue(
            flat_dict_partially_equal(inst_options, new_opts),
            f"inst_options={inst_options}, new_opt={new_opts}",
        )
        # Make sure the structure didn't change.
        self.assertTrue(
            dict_keys_equal(inst_options, asdict(opt_cls())),
            f"inst_options={inst_options}, original={opt_cls()}",
        )

    @data(EstimatorV2)
    def test_accept_level_1_options(self, primitive):
        """Test initializing options properly when given on level 1."""

        opt_cls = primitive._options_class
        options_dicts = [
            {},
            {"shots": 10},
            {"seed_simulator": 123},
            {"skip_transpilation": True, "log_level": "ERROR"},
            {"initial_layout": [1, 2], "shots": 100, "optimization_level": 2},
        ]

        expected_list = [opt_cls() for _ in range(len(options_dicts))]
        expected_list[1].execution.shots = 10
        expected_list[2].simulator.seed_simulator = 123
        expected_list[3].transpilation.skip_transpilation = True
        expected_list[3].environment.log_level = "ERROR"
        expected_list[4].transpilation.initial_layout = [1, 2]
        expected_list[4].execution.shots = 100
        expected_list[4].optimization_level = 2

        session = MagicMock(spec=MockSession)
        for opts, expected in zip(options_dicts, expected_list):
            with self.subTest(options=opts):
                inst1 = primitive(session=session, options=opts)
                inst2 = primitive(session=session, options=expected)
                self.assertEqual(inst1.options, inst2.options)

    @skip("We don't change default error level anymore")
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
                    inst.run(self.circ, observables=self.obs)
                else:
                    inst.run(self.circ)

                if sys.version_info >= (3, 8):
                    inputs = session.run.call_args.kwargs["inputs"]
                else:
                    _, kwargs = session.run.call_args
                    inputs = kwargs["inputs"]
                self.assertEqual(
                    inputs["transpilation"]["optimization_level"],
                    Options._DEFAULT_OPTIMIZATION_LEVEL,
                )
                self.assertEqual(
                    inputs["resilience_level"],
                    Options._DEFAULT_RESILIENCE_LEVEL,
                )

                session.service.backend().configuration().simulator = False
                inst = cls(session=session)
                inst.run(self.circ, observables=self.obs)
                if sys.version_info >= (3, 8):
                    inputs = session.run.call_args.kwargs["inputs"]
                else:
                    _, kwargs = session.run.call_args
                    inputs = kwargs["inputs"]
                self.assertEqual(
                    inputs["transpilation"]["optimization_level"],
                    Options._DEFAULT_OPTIMIZATION_LEVEL,
                )
                self.assertEqual(
                    inputs["resilience_level"],
                    Options._DEFAULT_RESILIENCE_LEVEL,
                )

                session.service.backend().configuration().simulator = True
                inst = cls(session=session)
                inst.run(self.circ, observables=self.obs)
                if sys.version_info >= (3, 8):
                    inputs = session.run.call_args.kwargs["inputs"]
                else:
                    _, kwargs = session.run.call_args
                    inputs = kwargs["inputs"]
                self.assertEqual(
                    inputs["transpilation"]["optimization_level"],
                    1,
                )
                self.assertEqual(inputs["resilience_level"], 0)

    @data(EstimatorV2)
    def test_raise_faulty_qubits(self, primitive):
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

        inst = primitive(session=session, options={"skip_transpilation": True})

        if isinstance(inst, IBMBaseEstimator):
            pub = (transpiled, observable)
        else:
            transpiled.measure_all()
            pub = (transpiled,)

        with self.assertRaises(ValueError) as err:
            inst.run(pubs=pub)
        self.assertIn(f"faulty qubit {faulty_qubit}", str(err.exception))

    @data(EstimatorV2)
    def test_raise_faulty_qubits_many(self, primitive):
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

        inst = primitive(session=session, options={"skip_transpilation": True})
        if isinstance(inst, IBMBaseEstimator):
            pubs = [(transpiled[0], observable), (transpiled[1], observable)]
        else:
            for circ in transpiled:
                circ.measure_all()
            pubs = [(transpiled[0],), (transpiled[1],)]

        with self.assertRaises(ValueError) as err:
            inst.run(pubs=pubs)
        self.assertIn(f"faulty qubit {faulty_qubit}", str(err.exception))

    @data(EstimatorV2)
    def test_raise_faulty_edge(self, primitive):
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

        inst = primitive(session=session, options={"skip_transpilation": True})
        if isinstance(inst, IBMBaseEstimator):
            pub = (transpiled, observable)
        else:
            transpiled.measure_all()
            pub = (transpiled,)

        with self.assertRaises(ValueError) as err:
            inst.run(pubs=pub)
        self.assertIn("cx", str(err.exception))
        self.assertIn(f"faulty edge {tuple(edge_qubits)}", str(err.exception))

    @data(EstimatorV2)
    def test_faulty_qubit_not_used(self, primitive):
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

        inst = primitive(session=session, options={"skip_transpilation": True})
        if isinstance(inst, IBMBaseEstimator):
            pub = (transpiled, observable)
        else:
            transpiled.measure_active(inplace=True)
            pub = (transpiled,)

        with patch.object(Session, "run") as mock_run:
            inst.run(pub)
        mock_run.assert_called_once()

    @data(EstimatorV2)
    def test_faulty_edge_not_used(self, primitive):
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

        inst = primitive(session=session, options={"skip_transpilation": True})
        if isinstance(inst, IBMBaseEstimator):
            pub = (transpiled, observable)
        else:
            transpiled.measure_all()
            pub = (transpiled,)

        with patch.object(Session, "run") as mock_run:
            inst.run(pub)
        mock_run.assert_called_once()

    @data(EstimatorV2)
    def test_no_raise_skip_transpilation(self, primitive):
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

        inst = primitive(session=session)
        if isinstance(inst, IBMBaseEstimator):
            pub = (transpiled, observable)
        else:
            transpiled.measure_all()
            pub = (transpiled,)

        with patch.object(Session, "run") as mock_run:
            inst.run(pub)
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

    @skip("Q-Ctrl does not support v2 yet")
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
                        _ = inst.run(self.circ, observables=self.obs, **options)
                    else:
                        _ = inst.run(self.circ, **options)

    @skip("Q-Ctrl does not support v2 yet")
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
                            _ = inst.run(self.circ, **bad_opt)
                        else:
                            _ = inst.run(self.circ, observables=self.obs, **bad_opt)

                        self.assertIn(expected_message, str(exc.exception))
