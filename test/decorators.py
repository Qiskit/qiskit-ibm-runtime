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
from functools import wraps
from typing import TYPE_CHECKING, Any
from unittest import SkipTest
from unittest.mock import patch

from ddt import named_data
from ibm_cloud_sdk_core import IAMTokenManager
from ibm_cloud_sdk_core.authenticators import NoAuthAuthenticator
from responses import RequestsMock

from qiskit_ibm_runtime.accounts.account import Account

from .registries import DefaultRegistry

if TYPE_CHECKING:
    from collections.abc import Callable

    from .registries import BaseRegistry


def mock_responses(
    func_or_registry: Callable | type[BaseRegistry] = DefaultRegistry,
    expose_responses_mock: bool = False,
) -> Callable:
    """Decorator that mocks the HTTP responses using a registry.

    When decorating a test, this decorator:
    * intercepts HTTP requests and returns mocked HTTP responses, based on a ``Registry``, which
      is added as an ``registry`` argument to the wrapped test.
    * patches low-level method related to IAM authentication, to simplify the authentication flow.
    * optionally exposes the responses mock as ``responses`` argument to the wrapped test.

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
        expose_responses_mock: if ``True``, the ``responses`` will be added to the list of arguments
            of the decorated tests.

    Can be used bare (``@mock_authentication``, using the default registry) or called with a
    registry class (``@mock_authentication(SomeRegistry)``).
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
                    Account, "get_iam_authentificator", return_value=NoAuthAuthenticator()
                ),
                patch.object(IAMTokenManager, "get_token", return_value="bearer token"),
                # Patch HTTP responses, allowing using a custom registry.
                RequestsMock(
                    registry=registry, assert_all_requests_are_fired=False
                ) as responses_mock,
            ):
                if expose_responses_mock:
                    return test_method(
                        *args,
                        # Pass the registry (and optionally the responses mock) as keyword arguments
                        # to prevent colliding with other decorators (specially ``@combine``).
                        registry=responses_mock.get_registry(),
                        responses=responses_mock,
                        **kwargs,
                    )
                else:
                    return test_method(*args, registry=responses_mock.get_registry(), **kwargs)

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


def staging_only(func):
    """Decorator that runs a test only on staging services."""

    @wraps(func)
    def _wrapper(self, *args, **kwargs):
        if "dev" not in self.dependencies.url and "test" not in self.dependencies.url:
            raise SkipTest(f"Skipping integration test. {self} is not supported on production.")
        func(self, *args, **kwargs)

    return _wrapper


def run_integration_test(func):
    """Decorator that injects preinitialized service and device parameters.

    To be used in test cases whose dependencies are set by `integration_test_dependencies`.
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
    test over both the legacy sampler and the client-side sampler.
    Otherwise by default, the wrapped test is expanded only for the legacy sampler.

    The decorated tests receive a new argument that contains the sampler class.
    """
    from qiskit_ibm_runtime import SamplerV2 as LegacySampler
    from qiskit_ibm_runtime.executor_sampler import Sampler as ExecutorSampler

    implementations = (
        [("legacy", LegacySampler), ("executor", ExecutorSampler)]
        if os.getenv("QISKIT_IBM_TEST_SAMPLER_V2_IMPLEMENTATIONS") == "1"
        else [("legacy", LegacySampler)]
    )
    return named_data(*implementations)(test_func)
