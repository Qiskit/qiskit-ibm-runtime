# This code is part of Qiskit.
#
# (C) Copyright IBM 2026.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Fixtures shared by the unit tests."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast
from unittest.mock import patch

import pytest
from ibm_cloud_sdk_core import IAMTokenManager
from ibm_cloud_sdk_core.authenticators import NoAuthAuthenticator
from responses import RequestsMock

from qiskit_ibm_runtime.accounts.account import Account
from test.registries import DefaultRegistry

if TYPE_CHECKING:
    from collections.abc import Iterator

    from test.registries import BaseRegistry


@pytest.fixture
def responses(request: pytest.FixtureRequest) -> Iterator[RequestsMock]:
    """Return the ``responses`` mock that mocks HTTP responses.

    See the ``registry`` fixture for more details.
    """
    marker = request.node.get_closest_marker("registry")
    registry_class = marker.kwargs["registry_class"] if marker else DefaultRegistry

    with (
        # Patch authentication, in order to simplify flow.
        patch.object(Account, "get_iam_authentificator", return_value=NoAuthAuthenticator()),
        patch.object(IAMTokenManager, "get_token", return_value="bearer token"),
        # Patch HTTP responses, allowing using a custom registry.
        RequestsMock(registry=registry_class, assert_all_requests_are_fired=False) as mock,
    ):
        yield mock


@pytest.fixture
def registry(responses: RequestsMock) -> BaseRegistry:
    """Return a registry that mocks HTTP responses.

    This fixture:
    * intercepts HTTP requests and returns mocked HTTP responses, based on a ``Registry``.
    * patches low-level method related to IAM authentication, to simplify the authentication flow.
    * the registry used for the HTTP responses is the one given by the `registry` marker of
      the test, as `registry_class=...`, defaulting to `DefaultRegistry`.

    This fixture is meant to be used with the items in the ``registries`` module:
    * ``DefaultRegistry`` and its subclasses.
    * ``Instance`` and ``Backend`` for setting the behavior.

    Example::

        def test_with_a_backend(self, registry):
            # Add a backend to the instance "a".
            registry.add_backend(Backend("some_new_backend"))
            ...

        @pytest.mark.registry(registry_class=OneInstanceNoBackendsRegistry)
        def test_with_a_specific_registry(self, registry):
            ...

        def test_something(self, registry, responses):
            ...
            assert len(responses.calls) == 1
    """
    return cast("BaseRegistry", responses.get_registry())


@pytest.fixture
def test_id(request: pytest.FixtureRequest) -> str:
    """Return the dotted id of the test, as `package.module.Class.method`.

    This replaces `unittest`'s `TestCase.id()`, which tests use both to name per-test loggers
    and to derive nested directories for saved artifacts.
    """
    return f"{request.node.module.__name__}.{request.node.cls.__name__}.{request.node.name}"
