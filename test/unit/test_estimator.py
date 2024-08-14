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

"""Tests for estimator class."""

import numpy as np
from ddt import data, ddt

from qiskit import QuantumCircuit, transpile
from qiskit.circuit.library import RealAmplitudes
from qiskit.quantum_info import SparsePauliOp, Pauli
from qiskit.primitives.containers.estimator_pub import EstimatorPub

from qiskit_ibm_runtime import Session, EstimatorV2, EstimatorOptions, IBMInputValueError
from qiskit_ibm_runtime.fake_provider import FakeSherbrooke

from .mock.fake_runtime_service import FakeRuntimeService
from ..ibm_test_case import IBMTestCase
from ..utils import (
    get_mocked_backend,
    dict_paritally_equal,
    transpile_pubs,
    get_primitive_inputs,
    remap_observables,
    get_transpiled_circuit,
)


@ddt
class TestEstimatorV2(IBMTestCase):
    """Class for testing the Estimator class."""

    @data(
        [(RealAmplitudes(num_qubits=2, reps=1), ["ZZ"], [[1, 2, 3, 4]])],
        [(RealAmplitudes(num_qubits=2, reps=1), ["ZZ", "YY"], [[1, 2, 3, 4]])],
        [(QuantumCircuit(2), ["XX"])],
        [(RealAmplitudes(num_qubits=1, reps=1), ["I"], [[1, 2]]), (QuantumCircuit(3), ["YYY"])],
    )
    def test_run_program_inputs(self, abs_pubs):
        """Verify program inputs are correct."""
        backend = get_mocked_backend()
        t_pubs = transpile_pubs(abs_pubs, backend, "estimator")

        inst = EstimatorV2(backend=backend)
        inst.run(t_pubs)
        input_params = backend.service.run.call_args.kwargs["inputs"]
        self.assertIn("pubs", input_params)
        pubs_param = input_params["pubs"]
        for a_pub_param, an_in_taks in zip(pubs_param, t_pubs):
            self.assertIsInstance(a_pub_param, EstimatorPub)
            # Check circuit
            self.assertEqual(a_pub_param.circuit, an_in_taks[0])
            # Check observables
            a_pub_obs = a_pub_param.observables.tolist()
            for a_pub_obs, an_input_obs in zip(a_pub_param.observables.tolist(), an_in_taks[1]):
                self.assertEqual(list(a_pub_obs.keys())[0], an_input_obs)
            # Check parameter values
            an_input_params = an_in_taks[2] if len(an_in_taks) == 3 else []
            param_values_array = list(a_pub_param.parameter_values.data.values())
            a_pub_param_values = param_values_array[0] if param_values_array else param_values_array
            np.testing.assert_allclose(a_pub_param_values, an_input_params)

    def test_unsupported_values_for_estimator_options(self):
        """Test exception when options levels are not supported."""
        options_bad = [
            {"resilience_level": 4, "optimization_level": 1},
            {"optimization_level": 4, "resilience_level": 2},
        ]

        with Session(
            service=FakeRuntimeService(channel="ibm_quantum", token="abc"),
            backend="common_backend",
        ) as session:
            for bad_opt in options_bad:
                inst = EstimatorV2(session=session)
                with self.assertRaises(ValueError) as exc:
                    inst.options.update(**bad_opt)
                self.assertIn(list(bad_opt.keys())[0], str(exc.exception))

    def test_invalid_estimator_precision_option(self):
        """Test exception when precision is invalid."""

        backend = get_mocked_backend()
        backend.configuration().simulator = True

        estimator = EstimatorV2(backend=backend)
        with self.assertRaises(ValueError) as exc:
            estimator.run(**get_primitive_inputs(estimator), precision=0)
        self.assertIn("The precision value must be strictly greater than 0", str(exc.exception))

    def test_pec_simulator(self):
        """Test error is raised when using pec on simulator without coupling map."""
        backend = get_mocked_backend()
        backend.configuration().simulator = True

        inst = EstimatorV2(backend=backend, options={"resilience": {"pec_mitigation": True}})
        with self.assertRaises(ValueError) as exc:
            inst.run(**get_primitive_inputs(inst))
        self.assertIn("coupling map", str(exc.exception))

    def test_run_default_options(self):
        """Test run using default options."""
        backend = get_mocked_backend()
        options_vars = [
            (
                EstimatorOptions(default_shots=1024),  # pylint: disable=unexpected-keyword-arg
                {"default_shots": 1024},
            ),
            (
                EstimatorOptions(optimization_level=1),  # pylint: disable=unexpected-keyword-arg
                {"transpilation": {"optimization_level": 1}},
            ),
            (
                {
                    "default_precision": 0.1,
                    "dynamical_decoupling": {"enable": True},
                },
                {
                    "default_precision": 0.1,
                    "dynamical_decoupling": {"enable": True},
                },
            ),
        ]
        for options, expected in options_vars:
            with self.subTest(options=options):
                inst = EstimatorV2(backend=backend, options=options)
                inst.run(**get_primitive_inputs(inst, backend=backend))
                options = backend.service.run.call_args.kwargs["inputs"]["options"]
                self.assertTrue(
                    dict_paritally_equal(options, expected),
                    f"{options} and {expected} not partially equal.",
                )

    @data(
        {"zne_extrapolator": "bad_extrapolator"},
        {"zne_extrapolator": "double_exponential", "zne_noise_factors": [1]},
    )
    def test_invalid_resilience_options(self, res_opt):
        """Test invalid resilience options."""
        backend = get_mocked_backend()
        with self.assertRaises(ValueError) as exc:
            inst = EstimatorV2(backend=backend, options={"resilience": res_opt})
            inst.run(**get_primitive_inputs(inst, backend))
        self.assertIn(list(res_opt.values())[0], str(exc.exception))
        if len(res_opt.keys()) > 1:
            self.assertIn(list(res_opt.keys())[1], str(exc.exception))

    def test_observable_types_single_circuit(self):
        """Test different observable types for a single circuit."""
        all_obs = [
            "IX",
            Pauli("YZ"),
            SparsePauliOp(["IX", "YZ"]),
            {"YZ": 1 + 2j},
            {Pauli("XX"): 1 + 2j},
            ["XX", "YY"],
            [Pauli("XX"), Pauli("YY")],
            [SparsePauliOp(["XX"], [2]), SparsePauliOp(["YY"], [1])],
            [
                {"XX": 1},
                {"YY": 2},
            ],
            [
                {Pauli("XX"): 1},
                {Pauli("YY"): 2},
            ],
        ]

        backend = get_mocked_backend()
        circuit = QuantumCircuit(2, 2)
        circuit.h(0)
        circuit.cx(0, 1)
        isa_circuit = transpile(circuit, backend=backend)

        estimator = EstimatorV2(backend=backend)
        for obs in all_obs:
            with self.subTest(obs=obs):
                pub = (isa_circuit, remap_observables(obs, isa_circuit))
                estimator.run([pub])

    def test_observable_types_multi_circuits(self):
        """Test different observable types for multiple circuits."""
        all_obs = [
            ["XX", "YYY"],
            [Pauli("XX"), Pauli("YYY")],
            [SparsePauliOp(["XX"]), SparsePauliOp(["YYY"])],
            [
                {"XX": 1 + 2j},
                {"YYY": 1 + 2j},
            ],
            [
                {Pauli("XX"): 1 + 2j},
                {Pauli("YYY"): 1 + 2j},
            ],
            [["XX", "YY"], ["ZZZ", "III"]],
            [[Pauli("XX"), Pauli("YY")], [Pauli("XXX"), Pauli("YYY")]],
            [
                [SparsePauliOp(["XX", "YY"], [1, 2]), SparsePauliOp(["YY", "-XX"], [2, 1])],
                [SparsePauliOp(["XXX"], [1]), SparsePauliOp(["YYY"], [2])],
            ],
            [[{"XX": 1}, {"YY": 2}], [{"XXX": 1}, {"YYY": 2}]],
            [
                [{Pauli("XX"): 1}, {Pauli("YY"): 2}],
                [{Pauli("XXX"): 1}, {Pauli("YYY"): 2}],
            ],
        ]

        backend = get_mocked_backend()
        circuit1 = get_transpiled_circuit(backend, num_qubits=2, measure=False)
        circuit2 = get_transpiled_circuit(backend, num_qubits=3, measure=False)
        estimator = EstimatorV2(backend=backend)
        for obs in all_obs:
            with self.subTest(obs=obs):
                obs1 = remap_observables(obs[0], circuit1)
                obs2 = remap_observables(obs[1], circuit2)
                estimator.run(pubs=[(circuit1, obs1), (circuit2, obs2)])

    def test_invalid_basis(self):
        """Test observable containing invalid basis."""
        all_obs = [
            ["JJ"],
            {"JJ": 1 + 2j},
            [["0J", "YY"]],
            [
                [
                    {"XX": 1 + 2j},
                    {"JJ": 1 + 2j},
                ]
            ],
        ]

        circuit = QuantumCircuit(2)
        estimator = EstimatorV2(backend=get_mocked_backend())
        for obs in all_obs:
            with self.subTest(obs=obs):
                with self.assertRaises(ValueError):
                    estimator.run((circuit, obs))

    def test_unsupported_dynamical_decoupling_with_dynamic_circuits(self):
        """Test that running on dynamic circuits with dynamical decoupling enabled is not allowed"""
        dynamic_circuit = QuantumCircuit(3, 1)
        dynamic_circuit.h(0)
        dynamic_circuit.measure(0, 0)
        dynamic_circuit.if_else(
            (0, True), QuantumCircuit(3, 1), QuantumCircuit(3, 1), [0, 1, 2], [0]
        )

        in_pubs = [(dynamic_circuit, ["XXX"])]
        backend = get_mocked_backend()
        inst = EstimatorV2(backend=backend)
        inst.options.dynamical_decoupling.enable = True
        with self.assertRaisesRegex(
            IBMInputValueError,
            "Dynamical decoupling currently cannot be used with dynamic circuits",
        ):
            inst.run(in_pubs)

    def test_estimator_validations(self):
        """Test exceptions when failing client-side validations."""
        backend = get_mocked_backend()
        inst = EstimatorV2(backend=backend)
        circ = QuantumCircuit(2)
        obs = []
        with self.assertRaisesRegex(ValueError, "Empty observables array is not allowed"):
            inst.run(pubs=[(circ, obs)])

    def test_gate_not_in_target(self):
        """Test exception when circuits contain gates that are not basis gates"""
        # pylint: disable=invalid-name,not-context-manager
        backend = FakeSherbrooke()
        estimator = EstimatorV2(backend=backend)
        observable = SparsePauliOp("Z")

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
            estimator.run(pubs=[(circ, observable)])
