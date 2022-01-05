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

"""Test the hello_world."""

import json
from test.fake_user_messenger import FakeUserMessenger
from unittest import TestCase
from qiskit.providers.aer import AerSimulator
from qiskit.providers.ibmq.runtime.utils import RuntimeEncoder, RuntimeDecoder
from qiskit_runtime.hello_world import hello_world


class TestHelloWorld(TestCase):
    """Test hello_world."""

    def setUp(self) -> None:
        """Test case setup."""
        self.backend = AerSimulator()
        user_messenger = FakeUserMessenger()
        self.user_messenger = user_messenger

    def test_hello_world(self):
        """Test hello_world."""
        inputs = {"iterations": 2}
        serialized_inputs = json.dumps(inputs, cls=RuntimeEncoder)
        unserialized_inputs = json.loads(serialized_inputs, cls=RuntimeDecoder)
        hello_world.main(self.backend, self.user_messenger, **unserialized_inputs)
        self.assertEqual(self.user_messenger.call_count, inputs["iterations"])
