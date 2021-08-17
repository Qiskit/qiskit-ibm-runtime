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

"""Fake UserMessenger.

This class is a fake UserMessenger.
"""

from typing import Any, Type
import json
from qiskit.providers.ibmq.runtime.utils import RuntimeEncoder


class FakeUserMessenger:
    """Fake UserMessenger."""

    def __init__(self):
        self.call_count = 0
        self.message = None

    def publish(
        self,
        message: Any,
        encoder: Type[json.JSONEncoder] = RuntimeEncoder,  # pylint: disable=unused-argument
        final: bool = False,  # pylint: disable=unused-argument
    ):
        """Fake publish for UserMessenger.

        Increments the number of times this method is called and stores the message arg.
        """
        self.message = message
        self.call_count += 1
