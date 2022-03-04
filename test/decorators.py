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

from qiskit_ibm_runtime import IBMRuntimeService
from .unit.mock.fake_runtime_service import FakeRuntimeService


def run_legacy_and_cloud_fake(func):
    """Decorator that runs a test using both legacy and cloud fake services."""

    @wraps(func)
    def _wrapper(self, *args, **kwargs):
        legacy_service = FakeRuntimeService(
            auth="legacy", token="my_token", instance="h/g/p"
        )
        cloud_service = FakeRuntimeService(
            auth="cloud",
            token="my_token",
            instance="crn:v1:bluemix:public:quantum-computing:my-region:a/...:...::",
        )
        for service in [legacy_service, cloud_service]:
            with self.subTest(service=service.auth):
                kwargs["service"] = service
                func(self, *args, **kwargs)

    return _wrapper


def _get_integration_test_config():
    token, url, instance = (
        os.getenv("QISKIT_IBM_TOKEN"),
        os.getenv("QISKIT_IBM_URL"),
        os.getenv("QISKIT_IBM_INSTANCE"),
    )
    auth: Any = "legacy" if url.find("quantum-computing.ibm.com") >= 0 else "cloud"
    return auth, token, url, instance


def run_integration_test(func):
    """Decorator that injects preinitialized service and device parameters.

    To be used in combinatino with the integration_test_setup decorator function."""

    @wraps(func)
    def _wrapper(self, *args, **kwargs):
        with self.subTest(service=self.dependencies.service):
            if self.dependencies.service:
                kwargs["service"] = self.dependencies.service
            func(self, *args, **kwargs)

    return _wrapper


def integration_test_setup(
    supported_auth: Optional[List[str]] = None,
    init_service: Optional[bool] = True,
) -> Callable:
    """Returns a decorator for integration test initialization.

    Args:
        supported_auth: a list of auth types that this test supports
        init_service: to initialize the IBMRuntimeService based on the current environment
            configuration and return it via the test dependencies

    Returns:
        A decorator that handles initialization of integration test dependencies.
    """

    def _decorator(func):
        @wraps(func)
        def _wrapper(self, *args, **kwargs):
            _supported_auth = (
                ["cloud", "legacy"] if supported_auth is None else supported_auth
            )

            auth, token, url, instance = _get_integration_test_config()
            if not all([auth, token, url]):
                raise Exception("Configuration Issue")

            if auth not in _supported_auth:
                raise SkipTest(
                    f"Skipping integration test. Test does not support auth type {auth}"
                )

            service = None
            if init_service:
                service = IBMRuntimeService(
                    auth=auth, token=token, url=url, instance=instance
                )
            dependencies = IntegrationTestDependencies(
                auth=auth,
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

    service: IBMRuntimeService
    instance: Optional[str]
    token: str
    auth: str
    url: str
