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


from qiskit import QuantumCircuit
from qiskit.quantum_info import SparsePauliOp, Pauli, random_hermitian, random_pauli_list
from qiskit.circuit import Parameter

import numpy as np

from qiskit_ibm_runtime import Estimator, Session

from .mock.fake_runtime_service import FakeRuntimeService
from ..ibm_test_case import IBMTestCase
from ..utils import get_mocked_backend
from .mock.fake_runtime_service import FakeRuntimeService


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

    def test_observable_types_single_circuit(self):
        """Test different observable types for a single circuit."""
        all_obs = [
            "IX",
            Pauli("YZ"),
            SparsePauliOp(["IX", "YZ"]),
            {"YZ": 1 + 2j},
            {Pauli("XX"): 1 + 2j},
            random_hermitian((2, 2)),
            [["XX", "YY"]],
            [[Pauli("XX"), Pauli("YY")]],
            [[SparsePauliOp(["XX"]), SparsePauliOp(["YY"])]],
            [
                [
                    {"XX": 1 + 2j},
                    {"YY": 1 + 2j},
                ]
            ],
            [
                [
                    {Pauli("XX"): 1 + 2j},
                    {Pauli("YY"): 1 + 2j},
                ]
            ],
            [random_pauli_list(2, 2)],
        ]

        circuit = QuantumCircuit(2)
        estimator = Estimator(backend=get_mocked_backend())
        for obs in all_obs:
            with self.subTest(obs=obs):
                estimator.run(circuits=circuit, observables=obs)

    def test_observable_types_multi_circuits(self):
        """Test different observable types for multiple circuits."""
        num_qx = 2
        all_obs = [
            ["XX", "YY"],
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
            [["XX", "YY"]] * num_qx,
            [[Pauli("XX"), Pauli("YY")]] * num_qx,
            [[SparsePauliOp(["XX"]), SparsePauliOp(["YY"])]] * num_qx,
            [[{"XX": 1 + 2j}, {"YY": 1 + 2j}]] * num_qx,
            [[{Pauli("XX"): 1 + 2j}, {Pauli("YY"): 1 + 2j}]] * num_qx,
            [random_pauli_list(2, 2)] * num_qx,
        ]

        circuit = QuantumCircuit(2)
        estimator = Estimator(backend=get_mocked_backend())
        for obs in all_obs:
            with self.subTest(obs=obs):
                estimator.run(circuits=[circuit] * num_qx, observables=obs)

    def test_invalid_basis(self):
        """Test observable containing invalid basis."""
        all_obs = [
            "JJ",
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
        estimator = Estimator(backend=get_mocked_backend())
        for obs in all_obs:
            with self.subTest(obs=obs):
                with self.assertRaises(ValueError):
                    estimator.run(circuits=circuit, observables=obs)

    def test_single_parameter_single_circuit(self):
        """Test single parameter for a single cirucit."""
        theta = Parameter("θ")
        circuit = QuantumCircuit(2)
        circuit.rz(theta, 0)

        param_vals = [
            np.pi,
            [np.pi],
            [[np.pi]],
            np.array([np.pi]),
            np.array([[np.pi]]),
            [np.array([np.pi])],
            [[[np.pi], [np.pi / 2]]],
            {theta: np.pi},
            [{theta: np.pi}],
        ]

        estimator = Estimator(backend=get_mocked_backend())
        for val in param_vals:
            with self.subTest(val=val):
                estimator.run(circuits=circuit, observables="ZZ", parameter_values=val)

    def test_multiple_parameters_single_circuit(self):
        """Test multiple parameters for a single circuit."""
        theta = Parameter("θ")
        circuit = QuantumCircuit(2)
        circuit.rz(theta, [0, 1])

        param_vals = [
            [[np.pi, np.pi]],
            np.array([[np.pi, np.pi]]),
            [np.array([np.pi, np.pi])],
            [[[np.pi, np.pi], [np.pi / 2, np.pi / 2]]],
            {theta: [np.pi, np.pi / 2]},
            {theta: [[np.pi, np.pi / 2], [np.pi / 4, np.pi / 8]]},
            [{theta: [np.pi, np.pi / 2]}],
        ]

        estimator = Estimator(backend=get_mocked_backend())
        for val in param_vals:
            with self.subTest(val=val):
                estimator.run(circuits=circuit, observables="ZZ", parameter_values=val)

    def test_multiple_parameters_multiple_circuits(self):
        """Test multiple parameters for multiple circuits."""
        theta = Parameter("θ")
        circuit = QuantumCircuit(2)
        circuit.rz(theta, [0, 1])

        param_vals = [
            [[np.pi, np.pi], [0.5, 0.5]],
            [np.array([np.pi, np.pi]), np.array([0.5, 0.5])],
            [[[np.pi, np.pi], [np.pi / 2, np.pi / 2]], [[0.5, 0.5], [0.1, 0.1]]],
            [{theta: [[np.pi, np.pi / 2], [np.pi / 4, np.pi / 8]]}, {theta: [0.5, 0.5]}],
        ]

        estimator = Estimator(backend=get_mocked_backend())
        for val in param_vals:
            with self.subTest(val=val):
                estimator.run(circuits=[circuit] * 2, observables=["ZZ"] * 2, parameter_values=val)
