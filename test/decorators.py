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

"""Decorators used by unit tests."""

import os
from dataclasses import dataclass
from functools import wraps
from typing import Callable, Optional, List, Any
from unittest import SkipTest

from qiskit_ibm_runtime import QiskitRuntimeService

from .unit.mock.fake_runtime_service import FakeRuntimeService


def production_only(func):
    """Decorator that runs a test only on production services."""

    @wraps(func)
    def _wrapper(self, *args, **kwargs):
        if "dev" in self.dependencies.url:
            raise SkipTest(
                f"Skipping integration test. {self} is not supported on staging."
            )
        func(self, *args, **kwargs)

    return _wrapper


def quantum_only(func):
    """Decorator that runs a test using only ibm_quantum services."""

    @wraps(func)
    def _wrapper(self, service):
        if service._channel != "ibm_quantum":
            raise SkipTest(
                f"Skipping integration test. {self} does not support channel type {service._channel}"
            )
        func(self, service)

    return _wrapper


def run_quantum_and_cloud_fake(func):
    """Decorator that runs a test using both quantum and cloud fake services."""

    @wraps(func)
    def _wrapper(self, *args, **kwargs):
        ibm_quantum_service = FakeRuntimeService(
            channel="ibm_quantum", token="my_token", instance="h/g/p"
        )
        cloud_service = FakeRuntimeService(
            channel="ibm_cloud",
            token="my_token",
            instance="crn:v1:bluemix:public:quantum-computing:my-region:a/...:...::",
        )
        for service in [ibm_quantum_service, cloud_service]:
            with self.subTest(service=service.channel):
                kwargs["service"] = service
                func(self, *args, **kwargs)

    return _wrapper


def _get_integration_test_config():
    token, url, instance = (
        os.getenv("QISKIT_IBM_TOKEN"),
        os.getenv("QISKIT_IBM_URL"),
        os.getenv("QISKIT_IBM_INSTANCE"),
    )
    channel: Any = (
        "ibm_quantum" if url.find("quantum-computing.ibm.com") >= 0 else "ibm_cloud"
    )
    return channel, token, url, instance


def run_integration_test(func):
    """Decorator that injects preinitialized service and device parameters.

    To be used in combination with the integration_test_setup decorator function."""

    @wraps(func)
    def _wrapper(self, *args, **kwargs):
        with self.subTest(service=self.dependencies.service):
            if self.dependencies.service:
                kwargs["service"] = self.dependencies.service
            func(self, *args, **kwargs)

    return _wrapper


def integration_test_setup(
    supported_channel: Optional[List[str]] = None,
    init_service: Optional[bool] = True,
) -> Callable:
    """Returns a decorator for integration test initialization.

    Args:
        supported_channel: a list of channel types that this test supports
        init_service: to initialize the QiskitRuntimeService based on the current environment
            configuration and return it via the test dependencies

    Returns:
        A decorator that handles initialization of integration test dependencies.
    """

    def _decorator(func):
        @wraps(func)
        def _wrapper(self, *args, **kwargs):
            _supported_channel = (
                ["ibm_cloud", "ibm_quantum"]
                if supported_channel is None
                else supported_channel
            )

            channel, token, url, instance = _get_integration_test_config()
            if not all([channel, token, url]):
                raise Exception("Configuration Issue")

            if channel not in _supported_channel:
                raise SkipTest(
                    f"Skipping integration test. Test does not support channel type {channel}"
                )

            service = None
            if init_service:
                service = QiskitRuntimeService(
                    channel=channel, token=token, url=url, instance=instance
                )
            dependencies = IntegrationTestDependencies(
                channel=channel,
                token=token,
                url=url,
                instance=instance,
                service=service,
            )
            kwargs["dependencies"] = dependencies
            func(self, *args, **kwargs)

        return _wrapper

    return _decorator


@dataclass
class IntegrationTestDependencies:
    """Integration test dependencies."""

    service: QiskitRuntimeService
    instance: Optional[str]
    token: str
    channel: str
    url: str
