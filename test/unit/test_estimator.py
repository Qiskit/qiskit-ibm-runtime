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

from unittest.mock import MagicMock

from qiskit import QuantumCircuit
from qiskit.circuit.library import RealAmplitudes
from qiskit.quantum_info import SparsePauliOp, Pauli, random_pauli_list
import qiskit.quantum_info as qi

import numpy as np
from ddt import data, ddt

from qiskit_ibm_runtime import Estimator, Session, EstimatorV2, EstimatorOptions
from qiskit_ibm_runtime.qiskit.primitives import EstimatorTask

from .mock.fake_runtime_service import FakeRuntimeService
from ..ibm_test_case import IBMTestCase
from ..utils import get_mocked_backend, MockSession, dict_paritally_equal


class TestEstimator(IBMTestCase):
    """Class for testing the Estimator class."""

    def setUp(self) -> None:
        super().setUp()
        self.circuit = QuantumCircuit(1, 1)
        self.observables = SparsePauliOp.from_list([("I", 1)])

    def test_unsupported_values_for_estimator_options(self):
        """Test exception when options levels are not supported."""
        options_bad = [
            {"resilience_level": 4, "optimization_level": 3},
            {"optimization_level": 4, "resilience_level": 2},
        ]

        with Session(
            service=FakeRuntimeService(channel="ibm_quantum", token="abc"),
            backend="common_backend",
        ) as session:
            for bad_opt in options_bad:
                inst = Estimator(session=session)
                with self.assertRaises(ValueError) as exc:
                    _ = inst.run(self.circuit, observables=self.observables, **bad_opt)
                self.assertIn(list(bad_opt.keys())[0], str(exc.exception))


@ddt
class TestEstimatorV2(IBMTestCase):
    """Class for testing the Estimator class."""

    def setUp(self) -> None:
        super().setUp()
        self.circuit = QuantumCircuit(1, 1)
        self.observables = SparsePauliOp.from_list([("I", 1)])

    @data(
        [(RealAmplitudes(num_qubits=2, reps=1), ["ZZ"], [1, 2, 3, 4])],
        [(RealAmplitudes(num_qubits=2, reps=1), ["ZZ", "YY"], [1, 2, 3, 4])],
        [(QuantumCircuit(2), ["XX"])],
        [(RealAmplitudes(num_qubits=1, reps=1), ["I"], [1, 2]), (QuantumCircuit(3), ["YYY"])],
    )
    def test_run_program_inputs(self, in_tasks):
        """Verify program inputs are correct."""
        session = MagicMock(spec=MockSession)
        inst = EstimatorV2(session=session)
        inst.run(in_tasks)
        input_params = session.run.call_args.kwargs["inputs"]
        self.assertIn("tasks", input_params)
        tasks_param = input_params["tasks"]
        for a_task_param, an_in_taks in zip(tasks_param, in_tasks):
            self.assertIsInstance(a_task_param, EstimatorTask)
            # Check circuit
            self.assertEqual(a_task_param.circuit, an_in_taks[0])
            # Check observables
            a_task_obs = a_task_param.observables.tolist()
            for a_task_obs, an_input_obs in zip(a_task_param.observables.tolist(), an_in_taks[1]):
                self.assertEqual(list(a_task_obs.keys())[0], an_input_obs)
            # Check parameter values
            an_input_params = an_in_taks[2] if len(an_in_taks) == 3 else []
            np.allclose(a_task_param.parameter_values.vals, an_input_params)

    def test_unsupported_values_for_estimator_options(self):
        """Test exception when options levels are not supported."""
        options_bad = [
            {"resilience_level": 4, "optimization_level": 3},
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

    def test_res_level3_simulator(self):
        """Test the correct default error levels are used."""

        session = MagicMock(spec=MockSession)
        session.service.backend().configuration().simulator = True

        inst = EstimatorV2(session=session, options={"resilience_level": 3})
        with self.assertRaises(ValueError) as exc:
            inst.run((self.circuit, self.observables))
        self.assertIn("coupling map", str(exc.exception))

    def test_run_default_options(self):
        """Test run using default options."""
        session = MagicMock(spec=MockSession)
        options_vars = [
            (
                EstimatorOptions(resilience_level=1),  # pylint: disable=unexpected-keyword-arg
                {"resilience_level": 1},
            ),
            (
                EstimatorOptions(optimization_level=3),  # pylint: disable=unexpected-keyword-arg
                {"transpilation": {"optimization_level": 3}},
            ),
            (
                {
                    "transpilation": {"initial_layout": [1, 2]},
                    "execution": {"shots": 100},
                },
                {
                    "transpilation": {"initial_layout": [1, 2]},
                    "execution": {"shots": 100},
                },
            ),
        ]
        for options, expected in options_vars:
            with self.subTest(options=options):
                inst = EstimatorV2(session=session, options=options)
                inst.run((self.circuit, self.observables))
                inputs = session.run.call_args.kwargs["inputs"]
                self.assertTrue(
                    dict_paritally_equal(inputs, expected),
                    f"{inputs} and {expected} not partially equal.",
                )

    @data(
        {"zne_extrapolator": "bad_extrapolator"},
        {"zne_extrapolator": "double_exponential", "zne_noise_factors": [1]},
    )
    def test_invalid_resilience_options(self, res_opt):
        """Test invalid resilience options."""
        session = MagicMock(spec=MockSession)
        with self.assertRaises(ValueError) as exc:
            inst = EstimatorV2(session=session, options={"resilience": res_opt})
            inst.run((self.circuit, self.observables))
        self.assertIn(list(res_opt.values())[0], str(exc.exception))
        if len(res_opt.keys()) > 1:
            self.assertIn(list(res_opt.keys())[1], str(exc.exception))

    @data(True, False)
    def test_observable_types_single_circuit(self, to_task):
        """Test different observable types for a single circuit."""
        all_obs = [
            # TODO: Uncomment single ObservableArrayLike when supported
            # "IX",
            # Pauli("YZ"),
            # SparsePauliOp(["IX", "YZ"]),
            # {"YZ": 1 + 2j},
            # {Pauli("XX"): 1 + 2j},
            ["XX", "YY"],
            [qi.random_pauli_list(2)],
            [Pauli("XX"), Pauli("YY")],
            [SparsePauliOp(["XX"]), SparsePauliOp(["YY"])],
            [
                {"XX": 1 + 2j},
                {"YY": 1 + 2j},
            ],
            [
                {Pauli("XX"): 1 + 2j},
                {Pauli("YY"): 1 + 2j},
            ],
            [random_pauli_list(2, 2)],
            [random_pauli_list(2, 3) for _ in range(5)],
            np.array([["II", "XX", "YY"], ["ZZ", "XZ", "II"]], dtype=object),
        ]

        circuit = QuantumCircuit(2)
        estimator = EstimatorV2(backend=get_mocked_backend())
        for obs in all_obs:
            with self.subTest(obs=obs):
                task = (circuit, obs)
                if to_task:
                    task = EstimatorTask.coerce(task)
                estimator.run(task)

    def test_observable_types_multi_circuits(self):
        """Test different observable types for multiple circuits."""
        all_obs = [
            # TODO: Uncomment single ObservableArrayLike when supported
            # ["XX", "YYY"],
            # [Pauli("XX"), Pauli("YYY")],
            # [SparsePauliOp(["XX"]), SparsePauliOp(["YYY"])],
            # [
            #     {"XX": 1 + 2j},
            #     {"YYY": 1 + 2j},
            # ],
            # [
            #     {Pauli("XX"): 1 + 2j},
            #     {Pauli("YYY"): 1 + 2j},
            # ],
            [["XX", "YY"], ["ZZZ", "III"]],
            [[Pauli("XX"), Pauli("YY")], [Pauli("XXX"), Pauli("YYY")]],
            [
                [SparsePauliOp(["XX"]), SparsePauliOp(["YY"])],
                [SparsePauliOp(["XXX"]), SparsePauliOp(["YYY"])],
            ],
            [[{"XX": 1 + 2j}, {"YY": 1 + 2j}], [{"XXX": 1 + 2j}, {"YYY": 1 + 2j}]],
            [
                [{Pauli("XX"): 1 + 2j}, {Pauli("YY"): 1 + 2j}],
                [{Pauli("XXX"): 1 + 2j}, {Pauli("YYY"): 1 + 2j}],
            ],
            [random_pauli_list(2, 2), random_pauli_list(3, 2)],
        ]

        circuit1 = QuantumCircuit(2)
        circuit2 = QuantumCircuit(3)
        estimator = EstimatorV2(backend=get_mocked_backend())
        for obs in all_obs:
            with self.subTest(obs=obs):
                estimator.run(tasks=[(circuit1, obs[0]), (circuit2, obs[1])])

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
