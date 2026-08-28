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

"""Decorators used by unit tests."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import wraps
from typing import TYPE_CHECKING, Any
from unittest import SkipTest
from unittest.mock import patch

from ddt import named_data
from ibm_cloud_sdk_core import IAMTokenManager
from ibm_cloud_sdk_core.authenticators import NoAuthAuthenticator
from responses import RequestsMock

from qiskit_ibm_runtime import QiskitRuntimeService
from qiskit_ibm_runtime.accounts.account import CloudAccount

from .registries import DefaultRegistry
from .unit.mock.fake_runtime_service import FakeRuntimeService

if TYPE_CHECKING:
    from collections.abc import Callable

    from qiskit_ibm_runtime.accounts import ChannelType

    from .registries import BaseRegistry


def mock_responses(
    func_or_registry: Callable | type[BaseRegistry] = DefaultRegistry,
    expose_responses_mock: bool = False,
) -> Callable:
    """Decorator that mocks the HTTP responses using a registry.

    When decorating a test, this decorator:
    * intercepts HTTP requests and returns mocked HTTP responses, based on a ``Registry``, which
      is added as an argument to the test.
    * patches low-level method related to IAM authentication, to simplify the authentication flow.

    This decorator is meant to be used with the items in the ``registries`` module:
    * ``DefaultRegistry`` and its subclasses.
    * ``Instance`` and ``Backend`` for setting the behavior.

    Example::

        @mock_responses(OneInstanceNoBackendsRegistry)
        def test_with_a_backend(self, registry):
            # Add a backend to the instance "a".
            registry.add_backend(Backend("some_new_backend"))
            ...

        @mock_responses(expose_responses_mock=True)
        def test_something(self, registry, responses):
            ...
            self.assertEqual(len(responses.calls), 1)

    Args:
        func_or_registry: the ``Registry`` to use. If the decorator is used without parenthesis
            (``@mock_responses``), contains the test to decorate.
        expose_responses_mock: if ``True``, the ``response`` will be added to the list of arguments
            of the decorated tests.

    Can be used bare (``@mock_authentication``, using the default registry) or
    called with a registry class (``@mock_authentication(SomeRegistry)``). The
    instantiated registry is passed to the wrapped test as an extra argument.
    """
    # Bare use: the argument is the decorated test method, not a registry class.
    if not isinstance(func_or_registry, type):
        return mock_responses(DefaultRegistry)(func_or_registry)

    registry = func_or_registry

    def decorator(test_method: Callable) -> Callable:
        @wraps(test_method)
        def wrapper(*args: object, **kwargs: object) -> object:
            with (
                # Patch authentication, in order to simplify flow.
                patch.object(
                    CloudAccount, "get_iam_authentificator", return_value=NoAuthAuthenticator()
                ),
                patch.object(IAMTokenManager, "get_token", return_value="bearer token"),
                # Patch HTTP responses, allowing using a custom registry.
                RequestsMock(
                    registry=registry, assert_all_requests_are_fired=False
                ) as responses_mock,
            ):
                if expose_responses_mock:
                    return test_method(
                        *args, responses_mock.get_registry(), responses_mock, **kwargs
                    )
                else:
                    return test_method(*args, responses_mock.get_registry(), **kwargs)

        return wrapper

    return decorator


def production_only(func):
    """Decorator that runs a test only on production services."""

    @wraps(func)
    def _wrapper(self, *args, **kwargs):
        if "dev" in self.dependencies.url or "test" in self.dependencies.url:
            raise SkipTest(f"Skipping integration test. {self} is not supported on staging.")
        func(self, *args, **kwargs)

    return _wrapper


def run_cloud_fake(func):
    """Decorator that runs a test using fake cloud services."""

    @wraps(func)
    def _wrapper(self, *args, **kwargs):
        kwargs["service"] = FakeRuntimeService(
            channel="ibm_cloud",
            token="my_token",
            instance="crn:v1:bluemix:public:quantum-computing:my-region:a/...:...::",
        )
        func(self, *args, **kwargs)

    return _wrapper


def get_integration_test_config():
    """Return a tuple with the specified configuration from env vars."""
    token, url, instance, qpu = (
        os.getenv("QISKIT_IBM_TOKEN"),
        os.getenv("QISKIT_IBM_URL"),
        os.getenv("QISKIT_IBM_INSTANCE"),
        os.getenv("QISKIT_IBM_QPU"),
    )
    channel: str = "ibm_quantum_platform"
    return channel, token, url, instance, qpu


def run_integration_test(func):
    """Decorator that injects preinitialized service and device parameters.

    To be used in combination with the integration_test_setup decorator function.
    """

    @wraps(func)
    def _wrapper(self, *args, **kwargs):
        if self.dependencies.service:
            kwargs["service"] = self.dependencies.service
        func(self, *args, **kwargs)

    return _wrapper


def run_configured_sampler_implementations(
    test_func: Callable[..., Any],
) -> Callable[..., Any]:
    """Parameterize sampler tests based on the configured implementations.

    Set ``QISKIT_IBM_TEST_BOTH_SAMPLER_IMPLEMENTATIONS=1`` to expand the wrapped
    test over both the legacy sampler and the executor-based sampler.
    Otherwise by default, the wrapped test is expanded only for the legacy sampler.

    The decorated tests receive a new argument that contains the sampler class.
    """
    from qiskit_ibm_runtime import SamplerV2 as LegacySamplerV2
    from qiskit_ibm_runtime.executor_sampler import SamplerV2 as ExecutorSamplerV2

    implementations = (
        [("legacy", LegacySamplerV2), ("executor", ExecutorSamplerV2)]
        if os.getenv("QISKIT_IBM_TEST_SAMPLER_V2_IMPLEMENTATIONS") == "1"
        else [("legacy", LegacySamplerV2)]
    )
    return named_data(*implementations)(test_func)


def integration_test_setup(
    supported_channel: list[str] | None = None,
    init_service: bool | None = True,
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
                ["ibm_cloud", "ibm_quantum_platform"]
                if supported_channel is None
                else supported_channel
            )

            channel, token, url, instance, qpu = get_integration_test_config()
            if not all([channel, token, url]):
                raise Exception("Configuration Issue")

            if channel not in _supported_channel:
                raise SkipTest(
                    f"Skipping integration test. Test does not support channel type {channel}"
                )

            service = None
            if init_service:
                service = QiskitRuntimeService(
                    instance=instance,
                    channel=channel,
                    token=token,
                    url=url,
                )
            dependencies = IntegrationTestDependencies(
                channel=channel,
                token=token,
                url=url,
                instance=instance,
                qpu=qpu,
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
    instance: str | None
    qpu: str
    token: str
    channel: ChannelType
    url: str
