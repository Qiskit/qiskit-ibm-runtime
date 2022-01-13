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

"""Base class for handling communication with program users."""

import json
from typing import Any, Type

from ..utils.json import RuntimeEncoder


class UserMessenger:
    """Base class for handling communication with program users.

    The ``main()`` function of your runtime program will receive an instance
    of this class as the second parameter. You can then use the instance
    to send results back to the program user.
    """

    def publish(
        self,
        message: Any,
        encoder: Type[json.JSONEncoder] = RuntimeEncoder,
    ) -> None:
        """Publish message.

        You can use this method to publish messages, such as interim and final results,
        to the program user. The messages will be made immediately available to the user,
        but they may choose not to receive the messages.

        Args:
            message: Message to be published. Can be any type.
            encoder: An optional JSON encoder for serializing
        """
        # pylint: disable=unused-argument
        # Default implementation for testing.
        print(json.dumps(message, cls=encoder))
