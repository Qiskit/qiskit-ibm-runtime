# This code is part of qiskit-runtime.
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

"""Test the circuit runner program."""

import json
from test.fake_user_messenger import FakeUserMessenger
from unittest import TestCase

from qiskit.providers.aer import AerSimulator
from qiskit.providers.ibmq.runtime.utils import RuntimeEncoder, RuntimeDecoder
from qiskit.result.result import Result
from qiskit import QuantumCircuit
from qiskit_runtime.circuit_runner import circuit_runner


class TestCircuitRunner(TestCase):
    """Test circuit_runner."""

    def setUp(self) -> None:
        """Test case setup."""
        n = 6
        qc = QuantumCircuit(n)
        qc.x(range(0, n))
        qc.h(range(0, n))
        self.qc = qc
        self.backend = AerSimulator()
        self.user_messenger = FakeUserMessenger()

    def test_circuit_runner(self):
        """Test circuit_runner program."""
        inputs = {
            "circuits": self.qc,
            "optimization_level": 0,
            "initial_layout": [0, 1, 4, 7, 10, 12],
            "measurement_error_mitigation": False,
        }
        serialized_inputs = json.dumps(inputs, cls=RuntimeEncoder)
        unserialized_inputs = json.loads(serialized_inputs, cls=RuntimeDecoder)
        result = circuit_runner.main(
            backend=self.backend, user_messenger=self.user_messenger, **unserialized_inputs
        )
        self.assertEqual(self.user_messenger.call_count, 0)
        self.assertTrue(isinstance(Result.from_dict(result), Result))
