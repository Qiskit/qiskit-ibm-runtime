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

import json
from unittest.mock import patch

from qiskit.circuit.library import RealAmplitudes
from qiskit.test.reference_circuits import ReferenceCircuits
from qiskit.quantum_info import SparsePauliOp

from qiskit_ibm_runtime.utils.json import RuntimeEncoder
from qiskit_ibm_runtime.utils.utils import _hash
from qiskit_ibm_runtime.qiskit.primitives.utils import _circuit_key

from qiskit_ibm_runtime import Sampler
import qiskit_ibm_runtime.session as session_pkg
from ..ibm_test_case import IBMTestCase

from .mock.fake_runtime_service import FakeRuntimeService


class TestSampler(IBMTestCase):
    """Class for testing the Sampler class."""

    @classmethod
    def setUpClass(cls):
        cls.qx = ReferenceCircuits.bell()
        cls.obs = SparsePauliOp.from_list([("IZ", 1)])
        return super().setUpClass()

    def tearDown(self) -> None:
        super().tearDown()
        session_pkg._DEFAULT_SESSION = None

    def test_sampler_circuit_caching(self):
        """Test circuit caching in Sampler class"""

        pqc = RealAmplitudes(num_qubits=2, reps=2)
        pqc.measure_all()
        pqc2 = RealAmplitudes(num_qubits=2, reps=3)
        pqc2.measure_all()
        pqc_id = _hash(json.dumps(_circuit_key(pqc), cls=RuntimeEncoder))
        pqc2_id = _hash(json.dumps(_circuit_key(pqc2), cls=RuntimeEncoder))

        theta1 = [0, 1, 1, 2, 3, 5]
        theta2 = [0, 1, 2, 3, 4, 5, 6, 7]

        with Sampler(
            circuits=[pqc, pqc2],
            service=FakeRuntimeService(channel="ibm_quantum", token="abc"),
            options={"backend": "ibmq_qasm_simulator"},
        ) as sampler:

            with patch.object(sampler._session, "run") as mock_run:
                sampler.run([pqc], [theta1])
                run_kwargs = mock_run.call_args.kwargs
                run_args = mock_run.call_args.args
                print(f"Printing run_args in sampler: {run_args}")
                print(f"Printing run_kwargs in sampler: {run_kwargs}")
                self.assertEqual(
                    run_kwargs.get("inputs").get("circuits"),
                    {pqc_id: pqc, pqc2_id: pqc2},
                )
                self.assertEqual(run_kwargs.get("inputs").get("circuit_ids"), [pqc_id])

            with patch.object(sampler._session, "run") as mock_run:
                sampler.run([pqc2], [theta2])
                run_kwargs = mock_run.call_args.kwargs
                self.assertEqual(run_kwargs.get("inputs").get("circuits"), {})
                self.assertEqual(run_kwargs.get("inputs").get("circuit_ids"), [pqc2_id])
