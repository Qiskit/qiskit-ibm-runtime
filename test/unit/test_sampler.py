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

"""Tests for sampler class."""

from unittest.mock import MagicMock

from ddt import data, ddt, named_data, unpack
from packaging.version import Version, parse as parse_version
import numpy as np

from qiskit.version import get_version_info as get_qiskit_version_info
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
from qiskit.primitives.containers.sampler_pub import SamplerPub
from qiskit.circuit import Parameter
from qiskit.circuit.library import real_amplitudes
from qiskit.providers import BackendV2, Options
from qiskit.result import Result
from qiskit.result.models import ExperimentResult, ExperimentResultData
from qiskit.transpiler import Target
from qiskit_ibm_runtime import Session, SamplerV2, SamplerOptions, IBMInputValueError
from qiskit_ibm_runtime.fake_provider import FakeFractionalBackend, FakeSherbrooke, FakeCusco

from ..ibm_test_case import IBMTestCase
from ..utils import MockSession, dict_paritally_equal, get_mocked_backend, transpile_pubs
from .mock.fake_api_backend import FakeApiBackendSpecs
from .mock.fake_runtime_service import FakeRuntimeService


@ddt
class TestSamplerV2(IBMTestCase):
    """Class for testing the Estimator class."""

    def setUp(self) -> None:
        super().setUp()
        self.circuit = QuantumCircuit(1, 1)

    @data(
        [(real_amplitudes(num_qubits=2, reps=1), [1, 2, 3, 4])],
        [(QuantumCircuit(2),)],
        [(real_amplitudes(num_qubits=1, reps=1), [1, 2]), (QuantumCircuit(3),)],
    )
    def test_run_program_inputs(self, in_pubs):
        """Verify program inputs are correct."""
        backend = get_mocked_backend()
        t_pubs = transpile_pubs(in_pubs, backend, "sampler")
        inst = SamplerV2(mode=backend)
        inst.run(t_pubs)
        input_params = backend.service._run.call_args.kwargs["inputs"]
        self.assertIn("pubs", input_params)
        pubs_param = input_params["pubs"]
        for a_pub_param, an_in_taks in zip(pubs_param, t_pubs):
            self.assertIsInstance(a_pub_param, SamplerPub)
            # Check circuit
            self.assertEqual(a_pub_param.circuit, an_in_taks[0])
            # Check parameter values
            an_input_params = an_in_taks[1] if len(an_in_taks) == 2 else []
            param_values_array = list(a_pub_param.parameter_values.data.values())
            a_pub_param_values = param_values_array[0] if param_values_array else param_values_array
            np.testing.assert_allclose(a_pub_param_values, an_input_params)

    @data(
        {"resilience_level": 1},
        {"resilience": {"zne_mitigation": True}},
        {"execution": {"meas_type": "unclassified"}},
    )
    def test_unsupported_values_for_sampler_options(self, opt):
        """Test exception when options levels are not supported."""
        backend = get_mocked_backend()
        with Session(
            backend=backend,
        ) as session:
            inst = SamplerV2(mode=session)
            with self.assertRaises(ValueError) as exc:
                inst.options.update(**opt)
            self.assertIn(list(opt.keys())[0], str(exc.exception))

    def test_unsupported_dynamical_decoupling_with_dynamic_circuits(self):
        """Test that running on dynamic circuits with dynamical decoupling enabled is not allowed"""
        dynamic_circuit = QuantumCircuit(3, 1)
        dynamic_circuit.h(0)
        dynamic_circuit.measure(0, 0)
        dynamic_circuit.if_else(
            (0, True), QuantumCircuit(3, 1), QuantumCircuit(3, 1), [0, 1, 2], [0]
        )

        in_pubs = [(dynamic_circuit,)]
        backend = get_mocked_backend()
        inst = SamplerV2(mode=backend)
        inst.options.dynamical_decoupling.enable = True
        with self.assertRaisesRegex(
            IBMInputValueError,
            "Dynamical decoupling currently cannot be used with dynamic circuits",
        ):
            inst.run(in_pubs)

    def test_run_default_options(self):
        """Test run using default options."""
        session = MagicMock(spec=MockSession, _backend="common_backend")
        options_vars = [
            (
                SamplerOptions(  # pylint: disable=unexpected-keyword-arg
                    dynamical_decoupling={"sequence_type": "XX"}
                ),
                {"dynamical_decoupling": {"sequence_type": "XX"}},
            ),
            (
                SamplerOptions(default_shots=1000),  # pylint: disable=unexpected-keyword-arg
                {"default_shots": 1000},
            ),
            (
                {
                    "execution": {"init_qubits": True, "rep_delay": 0.01},
                },
                {
                    "execution": {"init_qubits": True, "rep_delay": 0.01},
                },
            ),
        ]
        for options, expected in options_vars:
            with self.subTest(options=options):
                inst = SamplerV2(mode=session, options=options)
                inst.run((self.circuit,))
                inputs = session._run.call_args.kwargs["inputs"]["options"]
                self.assertTrue(
                    dict_paritally_equal(inputs, expected),
                    f"{inputs} and {expected} not partially equal.",
                )

    def test_sampler_validations(self):
        """Test exceptions when failing client-side validations."""
        backend = get_mocked_backend()
        with Session(
            backend=backend,
        ) as session:
            inst = SamplerV2(mode=session)
            circ = QuantumCircuit(QuantumRegister(2), ClassicalRegister(0))
            with self.assertRaisesRegex(ValueError, "Classical register .* is of size 0"):
                inst.run([(circ,)])

            creg = ClassicalRegister(2, "not-an-identifier")
            circ = QuantumCircuit(QuantumRegister(2), creg)
            with self.assertRaisesRegex(
                ValueError, "Classical register names must be valid identifiers"
            ):
                inst.run([(circ,)])

            creg = ClassicalRegister(2, "lambda")
            circ = QuantumCircuit(QuantumRegister(2), creg)
            with self.assertRaisesRegex(
                ValueError, "Classical register names cannot be Python keywords"
            ):
                inst.run([(circ,)])

    def test_run_dynamic_circuit_with_fractional_opted(self):
        """Fractional opted backend can run dynamic circuits."""
        service = FakeRuntimeService(
            channel="ibm_quantum_platform",
            token="my_token",
            backend_specs=[FakeApiBackendSpecs(backend_name="FakeFractionalBackend")],
        )
        backend = service.backends("fake_fractional", use_fractional_gates=True)[0]

        dynamic_circuit = QuantumCircuit(3, 1)
        dynamic_circuit.measure(0, 0)
        dynamic_circuit.if_else(
            (0, True), QuantumCircuit(3, 1), QuantumCircuit(3, 1), [0, 1, 2], [0]
        )

        inst = SamplerV2(mode=backend)
        inst.run([dynamic_circuit])

    def test_run_fractional_circuit_without_fractional_opted(self):
        """Fractional non-opted backend cannot run fractional circuits."""
        service = FakeRuntimeService(
            channel="ibm_quantum_platform",
            token="my_token",
            backend_specs=[FakeApiBackendSpecs(backend_name="FakeFractionalBackend")],
        )
        backend = service.backends("fake_fractional", use_fractional_gates=False)[0]

        fractional_circuit = QuantumCircuit(1, 1)
        fractional_circuit.rx(1.23, 0)
        fractional_circuit.measure(0, 0)

        inst = SamplerV2(mode=backend)
        with self.assertRaises(IBMInputValueError):
            inst.run([fractional_circuit])

    @named_data(
        ("without_fractional", False),
    )
    def test_run_fractional_dynamic_mix(self, use_fractional):
        """Any backend cannot run mixture of fractional and dynamic circuits."""
        service = FakeRuntimeService(
            channel="ibm_quantum_platform",
            token="my_token",
            backend_specs=[FakeApiBackendSpecs(backend_name="FakeFractionalBackend")],
        )
        backend = service.backends("fake_fractional", use_fractional_gates=use_fractional)[0]

        dynamic_circuit = QuantumCircuit(3, 1)
        dynamic_circuit.measure(0, 0)
        dynamic_circuit.if_else(
            (0, True), QuantumCircuit(3, 1), QuantumCircuit(3, 1), [0, 1, 2], [0]
        )

        fractional_circuit = QuantumCircuit(1, 1)
        fractional_circuit.rx(1.23, 0)
        fractional_circuit.measure(0, 0)

        inst = SamplerV2(mode=backend)
        with self.assertRaises(IBMInputValueError):
            inst.run([dynamic_circuit, fractional_circuit])

    def test_gate_not_in_target(self):
        """Test exception when circuits contain gates that are not basis gates"""
        # pylint: disable=invalid-name,not-context-manager
        backend = FakeSherbrooke()
        sampler = SamplerV2(mode=backend)

        circ = QuantumCircuit(1, 1)
        circ.x(0)
        circ.measure(0, 0)
        with circ.if_test((0, 1)):
            with circ.if_test((0, 0)) as else_:
                circ.x(0)
            with else_:
                circ.h(0)
        circ.measure(0, 0)

        with self.assertRaisesRegex(IBMInputValueError, " h "):
            sampler.run(pubs=[circ])

    @data(FakeSherbrooke(), FakeCusco())
    def test_isa_inside_condition_block(self, backend):
        """Test no exception for 2q gates involving qubits that are not connected in
        the coupling map, inside control operation blocks; and yes exception for
        qubit pairs that are not connected"""
        # pylint: disable=invalid-name,not-context-manager

        circ = QuantumCircuit(5, 1)
        circ.x(0)
        circ.measure(0, 0)
        with circ.if_test((0, 1)):
            circ.ecr(1, 2)

        if backend.name == "fake_sherbrooke":
            SamplerV2(backend).run(pubs=[circ])
        else:
            with self.assertRaises(IBMInputValueError):
                SamplerV2(backend).run(pubs=[circ])

    @data(FakeSherbrooke(), FakeCusco())
    def test_isa_inside_condition_block_body_in_separate_circuit(self, backend):
        """Test no exception for 2q gates involving qubits that are not connected in
        the coupling map, inside control operation blocks; and yes exception for
        qubit pairs that are not connected.
        For the case where the control operation body is defined not in a
        context, as in `test_isa_inside_condition_block`, but in a separate circuit."""
        # pylint: disable=invalid-name,not-context-manager

        body = QuantumCircuit(QuantumRegister(2, "inner"))
        body.ecr(0, 1)

        circ = QuantumCircuit(5, 1)
        circ.x(0)
        circ.measure(0, 0)
        circ.if_test((circ.clbits[0], True), body, [1, 2], [])

        if backend.name == "fake_sherbrooke":
            SamplerV2(backend).run(pubs=[circ])
        else:
            with self.assertRaises(IBMInputValueError):
                SamplerV2(backend).run(pubs=[circ])

    @data(-1, 1, 2)
    def test_rzz_fixed_angle_validation(self, angle):
        """Test exception when rzz gate is used with an angle outside the range [0, pi/2]"""
        backend = FakeFractionalBackend()

        circ = QuantumCircuit(2)
        circ.rzz(angle, 0, 1)

        if angle == 1:
            SamplerV2(backend).run(pubs=[circ])
        else:
            with self.assertRaisesRegex(IBMInputValueError, f"{angle}"):
                SamplerV2(backend).run(pubs=[circ])

    @data(-1, 1, 2)
    def test_rzz_parametrized_angle_validation(self, angle):
        """Test exception when rzz gate is used with a parameter which is assigned a value outside
        the range [0, pi/2]"""
        backend = FakeFractionalBackend()
        param = Parameter("p")

        circ = QuantumCircuit(2)
        circ.rzz(param, 0, 1)

        if angle == 1:
            SamplerV2(backend).run(pubs=[(circ, [angle])])
        else:
            with self.assertRaisesRegex(IBMInputValueError, f"p={angle}"):
                SamplerV2(backend).run(pubs=[(circ, [angle])])

    @data([1.0, 2.0], [1.0, 0.0])
    @unpack
    def test_rzz_validation_param_exp(self, val1, val2):
        """Test exception when rzz gate is used with a parameter expression, which is evaluated to
        a value outside the range [0, pi/2]"""
        backend = FakeFractionalBackend()
        p1 = Parameter("p1")
        p2 = Parameter("p2")

        circ = QuantumCircuit(2)
        circ.rzz(2 * p2 + p1, 0, 1)

        if val2 == 0:
            SamplerV2(backend).run(pubs=[(circ, [val1, val2])])
        else:
            # order of the values is not guaranteed
            with self.assertRaisesRegex(
                IBMInputValueError, (rf"p2={val2}, p1={val1}" rf"|p1={val1}, p2={val2}")
            ):
                SamplerV2(backend).run(pubs=[(circ, [val1, val2])])

    @data(("a", -1.0), ("b", 2.0), ("d", 3.0), (-1.0, 1.0), (1.0, 2.0), None)
    def test_rzz_complex(self, flawed_params):
        """Testing rzz validation, a variation of test_rzz_parametrized_angle_validation which
        tests a more complex case. In addition, we test the currently non-existing case of dynamic
        instructions."""
        # pylint: disable=not-context-manager

        # FakeFractionalBackend has both fractional and dynamic instructions
        backend = FakeFractionalBackend()

        aparam = Parameter("a")
        bparam = Parameter("b")
        cparam = Parameter("c")
        dparam = Parameter("d")

        angle1 = 1
        angle2 = 1
        if flawed_params is not None and not isinstance(flawed_params[0], str):
            angle1 = flawed_params[0]
            angle2 = flawed_params[1]

        circ = QuantumCircuit(2, 1)
        circ.rzz(bparam, 0, 1)
        circ.rzz(angle1, 0, 1)
        circ.measure(0, 0)
        with circ.if_test((0, 1)):
            circ.rzz(aparam, 0, 1)
            circ.rzz(angle2, 0, 1)
        circ.rx(cparam, 0)
        circ.rzz(dparam, 0, 1)
        circ.rzz(1, 0, 1)
        circ.rzz(aparam, 0, 1)

        val_ab = np.ones([2, 2, 3, 2])
        val_c = (-1) * np.ones([2, 2, 3])
        val_d = np.ones([2, 2, 3])

        if flawed_params is not None and isinstance(flawed_params[0], str):
            if flawed_params[0] == "a":
                val_ab[0, 1, 1, 0] = flawed_params[1]
            if flawed_params[0] == "b":
                val_ab[1, 0, 2, 1] = flawed_params[1]
            if flawed_params[0] == "d":
                val_d[1, 1, 1] = flawed_params[1]

        pub = (circ, {("a", "b"): val_ab, "c": val_c, "d": val_d})

        if flawed_params is None:
            SamplerV2(backend).run(pubs=[pub])
        else:
            if isinstance(flawed_params[0], str):
                with self.assertRaisesRegex(
                    IBMInputValueError, f"{flawed_params[0]}={flawed_params[1]}"
                ):
                    SamplerV2(backend).run(pubs=[pub])
            else:
                with self.assertRaisesRegex(
                    IBMInputValueError, f"{flawed_params[0] * flawed_params[1]}"
                ):
                    SamplerV2(backend).run(pubs=[pub])

    @data(
        "classified",
        "kerneled",
        "avg_kerneled",
    )
    def test_backend_run_options(self, meas_type):
        """Test translation of sampler options into backend run options"""

        # This test is checking that meas_level, meas_return, and noise_model
        # get through the backend's run() call when SamplerV2 falls back to
        # BackendSamplerV2 in local mode. To do this, it creates a dummy
        # backend class that returns a result of the right format so that the
        # sampler execution completes successfully.

        if parse_version(get_qiskit_version_info()) < Version("1.3.0rc1"):
            self.skipTest("Feature not supported on this version of Qiskit")

        class DummyJob:
            """Enough of a job class to return a result"""

            def __init__(self, run_options):
                self.run_options = run_options

            def result(self):
                """Return result object"""
                shots = self.run_options["shots"]

                if self.run_options["meas_level"] == 1:
                    counts = None
                    if self.run_options["meas_return"] == "single":
                        memory = [[[0.0, 0.0]] * shots]
                    else:
                        memory = [[0.0, 0.0]]
                else:
                    counts = {"0": shots}
                    memory = ["0"] * shots
                result = Result(
                    backend_name="test_backend",
                    backend_version="0.0",
                    qobj_id="xyz",
                    job_id="123",
                    success=True,
                    results=[
                        ExperimentResult(
                            shots=100,
                            success=True,
                            data=ExperimentResultData(memory=memory, counts=counts),
                        )
                    ],
                )
                return result

        class DummyBackend(BackendV2):
            """Test backend that saves run options into the result"""

            max_circuits = 1
            # The backend gets cloned inside of the sampler execution code, so
            # it is difficult to get a handle on the actual backend used to run
            # the job. Here we save the run options into a class level variable
            # that can be checked after run() is called.
            used_run_options = {}

            def __init__(self, **kwargs):
                super().__init__(**kwargs)

                self._target = Target()

            @classmethod
            def _default_options(cls):
                return Options()

            @property
            def target(self):
                return self._target

            def run(self, run_input, **run_options):
                nonlocal used_run_options
                DummyBackend.used_run_options = run_options
                return DummyJob(run_options)

        backend = DummyBackend()

        circ = QuantumCircuit(1, 1)
        circ.measure(0, 0)

        sampler = SamplerV2(mode=backend)
        sampler.options.simulator.noise_model = {"name": "some_model"}
        sampler.options.execution.meas_type = meas_type

        job = sampler.run([circ], shots=100)
        result = job.result()

        used_run_options = DummyBackend.used_run_options
        self.assertDictEqual(used_run_options["noise_model"], {"name": "some_model"})

        if meas_type == "classified":
            self.assertEqual(used_run_options["meas_level"], 2)
            self.assertDictEqual(result[0].data.c.get_counts(), {"0": 100})
        elif meas_type == "kerneled":
            self.assertEqual(used_run_options["meas_level"], 1)
            self.assertEqual(used_run_options["meas_return"], "single")
            self.assertTrue(np.array_equal(result[0].data.c, np.zeros((1, 100))))
        else:  # meas_type == "avg_kerneled"
            self.assertEqual(used_run_options["meas_level"], 1)
            self.assertEqual(used_run_options["meas_return"], "avg")
            self.assertTrue(np.array_equal(result[0].data.c, np.zeros((1,))))
