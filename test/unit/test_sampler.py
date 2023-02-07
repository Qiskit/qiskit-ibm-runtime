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
import unittest

from qiskit.circuit.library import RealAmplitudes
from qiskit.primitives.utils import _circuit_key

from qiskit_ibm_runtime.utils.json import RuntimeEncoder
from qiskit_ibm_runtime.utils.utils import _hash
from qiskit_ibm_runtime import Sampler, Session

from ..ibm_test_case import IBMTestCase
from .mock.fake_runtime_service import FakeRuntimeService


class TestSampler(IBMTestCase):
    """Class for testing the Sampler class."""

    @unittest.skip("Skip until data caching is reenabled.")
    def test_sampler_circuit_caching(self):
        """Test circuit caching in Sampler class"""

        pqc = RealAmplitudes(num_qubits=2, reps=2)
        pqc.measure_all()
        pqc2 = RealAmplitudes(num_qubits=2, reps=3)
        pqc2.measure_all()
        pqc3 = RealAmplitudes(num_qubits=2, reps=2)
        pqc3.measure_all()
        pqc4 = RealAmplitudes(num_qubits=2, reps=3)
        pqc4.measure_all()
        pqc_id = _hash(json.dumps(_circuit_key(pqc), cls=RuntimeEncoder))
        pqc2_id = _hash(json.dumps(_circuit_key(pqc2), cls=RuntimeEncoder))
        pqc3_id = _hash(json.dumps(_circuit_key(pqc3), cls=RuntimeEncoder))
        pqc4_id = _hash(json.dumps(_circuit_key(pqc4), cls=RuntimeEncoder))

        with Session(
            service=FakeRuntimeService(channel="ibm_quantum", token="abc"),
            backend="ibmq_qasm_simulator",
        ) as session:
            sampler = Sampler(session=session)
            with patch.object(sampler._session, "run") as mock_run:
                sampler.run([pqc, pqc2], [[1] * 6, [1] * 8])
                _, kwargs = mock_run.call_args
                inputs = kwargs["inputs"]
                self.assertDictEqual(inputs["circuits"], {pqc_id: pqc, pqc2_id: pqc2})
                self.assertEqual(inputs["circuit_ids"], [pqc_id, pqc2_id])

            with patch.object(sampler._session, "run") as mock_run:
                sampler.run([pqc2], [[1] * 8])
                _, kwargs = mock_run.call_args
                inputs = kwargs["inputs"]
                self.assertDictEqual(inputs["circuits"], {})
                self.assertEqual(inputs["circuit_ids"], [pqc2_id])

            with patch.object(sampler._session, "run") as mock_run:
                sampler.run([pqc3], [[1] * 6])
                _, kwargs = mock_run.call_args
                inputs = kwargs["inputs"]
                self.assertDictEqual(inputs["circuits"], {pqc3_id: pqc3})
                self.assertEqual(inputs["circuit_ids"], [pqc3_id])

            with patch.object(sampler._session, "run") as mock_run:
                sampler.run([pqc4, pqc], [[1] * 8, [1] * 6])
                _, kwargs = mock_run.call_args
                inputs = kwargs["inputs"]
                self.assertDictEqual(inputs["circuits"], {pqc4_id: pqc4})
                self.assertEqual(inputs["circuit_ids"], [pqc4_id, pqc_id])
