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

from ddt import data, ddt
import numpy as np

from qiskit import QuantumCircuit
from qiskit.circuit.library import RealAmplitudes
from qiskit.test.reference_circuits import ReferenceCircuits
from qiskit_ibm_runtime import Sampler, Session, SamplerV2, SamplerOptions
from qiskit_ibm_runtime.qiskit.primitives import SamplerTask

from ..ibm_test_case import IBMTestCase
from .mock.fake_runtime_service import FakeRuntimeService
from ..utils import MockSession, dict_paritally_equal


class TestSampler(IBMTestCase):
    """Class for testing the Sampler class."""

    def test_unsupported_values_for_sampler_options(self):
        """Test exception when options levels are not supported."""
        options_bad = [
            {"resilience_level": 2, "optimization_level": 3},
            {"optimization_level": 4, "resilience_level": 1},
        ]

        with Session(
            service=FakeRuntimeService(channel="ibm_quantum", token="abc"),
            backend="common_backend",
        ) as session:
            circuit = ReferenceCircuits.bell()
            for bad_opt in options_bad:
                inst = Sampler(session=session)
                with self.assertRaises(ValueError) as exc:
                    _ = inst.run(circuit, **bad_opt)
                self.assertIn(list(bad_opt.keys())[0], str(exc.exception))


@ddt
class TestSamplerV2(IBMTestCase):
    """Class for testing the Estimator class."""

    def setUp(self) -> None:
        super().setUp()
        self.circuit = QuantumCircuit(1, 1)

    @data(
        [(RealAmplitudes(num_qubits=2, reps=1), [1, 2, 3, 4])],
        [(RealAmplitudes(num_qubits=2, reps=1), [1, 2, 3, 4])],
        [(QuantumCircuit(2),)],
        [(RealAmplitudes(num_qubits=1, reps=1), [1, 2]), (QuantumCircuit(3),)],
    )
    def test_run_program_inputs(self, in_tasks):
        """Verify program inputs are correct."""
        session = MagicMock(spec=MockSession)
        inst = SamplerV2(session=session)
        inst.run(in_tasks)
        input_params = session.run.call_args.kwargs["inputs"]
        self.assertIn("tasks", input_params)
        tasks_param = input_params["tasks"]
        for a_task_param, an_in_taks in zip(tasks_param, in_tasks):
            self.assertIsInstance(a_task_param, SamplerTask)
            # Check circuit
            self.assertEqual(a_task_param.circuit, an_in_taks[0])
            # Check parameter values
            an_input_params = an_in_taks[1] if len(an_in_taks) == 2 else []
            np.allclose(a_task_param.parameter_values.vals, an_input_params)

    @data(
        {"optimization_level": 4}, {"resilience_level": 1}, {"resilience": {"zne_mitigation": True}}
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

    def test_run_default_options(self):
        """Test run using default options."""
        session = MagicMock(spec=MockSession)
        options_vars = [
            (
                SamplerOptions(dynamical_decoupling="XX"),  # pylint: disable=unexpected-keyword-arg
                {"dynamical_decoupling": "XX"},
            ),
            (
                SamplerOptions(optimization_level=3),  # pylint: disable=unexpected-keyword-arg
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
                inst = SamplerV2(session=session, options=options)
                inst.run((self.circuit,))
                inputs = session.run.call_args.kwargs["inputs"]
                self.assertTrue(
                    dict_paritally_equal(inputs, expected),
                    f"{inputs} and {expected} not partially equal.",
                )
