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

from ddt import data, ddt, named_data
import numpy as np

from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
from qiskit.primitives.containers.sampler_pub import SamplerPub
from qiskit.circuit.library import RealAmplitudes
from qiskit_ibm_runtime import Session, SamplerV2, SamplerOptions, IBMInputValueError
from qiskit_ibm_runtime.fake_provider import FakeFractionalBackend, FakeSherbrooke

from ..ibm_test_case import IBMTestCase
from ..utils import MockSession, dict_paritally_equal, get_mocked_backend, transpile_pubs
from .mock.fake_runtime_service import FakeRuntimeService


@ddt
class TestSamplerV2(IBMTestCase):
    """Class for testing the Estimator class."""

    def setUp(self) -> None:
        super().setUp()
        self.circuit = QuantumCircuit(1, 1)

    @data(
        [(RealAmplitudes(num_qubits=2, reps=1), [1, 2, 3, 4])],
        [(QuantumCircuit(2),)],
        [(RealAmplitudes(num_qubits=1, reps=1), [1, 2]), (QuantumCircuit(3),)],
    )
    def test_run_program_inputs(self, in_pubs):
        """Verify program inputs are correct."""
        backend = get_mocked_backend()
        t_pubs = transpile_pubs(in_pubs, backend, "sampler")
        inst = SamplerV2(backend=backend)
        inst.run(t_pubs)
        input_params = backend.service.run.call_args.kwargs["inputs"]
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
        {"optimization_level": 4},
        {"resilience_level": 1},
        {"resilience": {"zne_mitigation": True}},
        {"execution": {"meas_type": "unclassified"}},
    )
    def test_unsupported_values_for_sampler_options(self, opt):
        """Test exception when options levels are not supported."""
        with Session(
            service=FakeRuntimeService(channel="ibm_quantum", token="abc"),
            backend="common_backend",
        ) as session:
            inst = SamplerV2(session=session)
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
        inst = SamplerV2(backend=backend)
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
                inst = SamplerV2(session=session, options=options)
                inst.run((self.circuit,))
                inputs = session.run.call_args.kwargs["inputs"]["options"]
                self.assertTrue(
                    dict_paritally_equal(inputs, expected),
                    f"{inputs} and {expected} not partially equal.",
                )

    def test_sampler_validations(self):
        """Test exceptions when failing client-side validations."""
        with Session(
            service=FakeRuntimeService(channel="ibm_quantum", token="abc"),
            backend="common_backend",
        ) as session:
            inst = SamplerV2(session=session)
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
        """Fractional opted backend cannot run dynamic circuits."""
        model_backend = FakeFractionalBackend()
        model_backend._set_props_dict_from_json()
        backend = get_mocked_backend(
            name="fake_fractional",
            configuration=model_backend._conf_dict,
            properties=model_backend._props_dict,
        )
        backend.options.use_fractional_gates = True

        dynamic_circuit = QuantumCircuit(3, 1)
        dynamic_circuit.measure(0, 0)
        dynamic_circuit.if_else(
            (0, True), QuantumCircuit(3, 1), QuantumCircuit(3, 1), [0, 1, 2], [0]
        )

        inst = SamplerV2(mode=backend)
        with self.assertRaises(IBMInputValueError):
            inst.run([dynamic_circuit])

    def test_run_fractional_circuit_without_fractional_opted(self):
        """Fractional non-opted backend cannot run fractional circuits."""
        model_backend = FakeFractionalBackend()
        model_backend._set_props_dict_from_json()
        backend = get_mocked_backend(
            name="fake_fractional",
            configuration=model_backend._conf_dict,
            properties=model_backend._props_dict,
        )
        backend.options.use_fractional_gates = False

        fractional_circuit = QuantumCircuit(1, 1)
        fractional_circuit.rx(1.23, 0)
        fractional_circuit.measure(0, 0)

        inst = SamplerV2(mode=backend)
        with self.assertRaises(IBMInputValueError):
            inst.run([fractional_circuit])

    @named_data(
        ("with_fractional", True),
        ("without_fractional", False),
    )
    def test_run_fractional_dynamic_mix(self, use_fractional):
        """Any backend cannot run mixture of fractional and dynamic circuits."""
        model_backend = FakeFractionalBackend()
        model_backend._set_props_dict_from_json()
        backend = get_mocked_backend(
            name="fake_fractional",
            configuration=model_backend._conf_dict,
            properties=model_backend._props_dict,
        )
        backend.options.use_fractional_gates = use_fractional

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
        sampler = SamplerV2(backend=backend)

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
            sampler.run(pubs=[(circ)])
