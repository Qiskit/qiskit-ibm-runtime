# This code is part of Qiskit.
#
# (C) Copyright IBM 2021-2026.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Custom TestCases for integration tests."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import TYPE_CHECKING

import pytest

from qiskit_ibm_runtime import QiskitRuntimeService

if TYPE_CHECKING:
    from qiskit_ibm_runtime.accounts import ChannelType


@dataclass
class Dependencies:
    """Integration test dependencies."""

    service: QiskitRuntimeService
    instance: str | None
    qpu: str
    token: str
    channel: ChannelType
    url: str


def integration_test_dependencies(init_service: bool = True) -> Dependencies:
    """Return the dependencies of an integration test, from the environment configuration.

    Args:
        init_service: whether to initialize the `QiskitRuntimeService` from the environment
            configuration. When `False`, the returned dependencies have no service.

    Returns:
        The dependencies of an integration test.

    """
    channel: ChannelType = "ibm_quantum_platform"
    token = os.getenv("QISKIT_IBM_TOKEN")
    url = os.getenv("QISKIT_IBM_URL")
    instance = os.getenv("QISKIT_IBM_INSTANCE")

    if not token or not url:
        pytest.skip("No integration test credentials available.")

    service = (
        QiskitRuntimeService(channel=channel, token=token, url=url, instance=instance)
        if init_service
        else None
    )

    return Dependencies(
        channel=channel,
        token=token,
        url=url,
        instance=instance,
        qpu=os.getenv("QISKIT_IBM_QPU"),
        service=service,
    )
