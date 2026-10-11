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

"""Fixtures shared by the integration tests."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from .case import integration_test_dependencies

if TYPE_CHECKING:
    from .case import IntegrationTestDependencies


@pytest.fixture(scope="class")
def dependencies() -> IntegrationTestDependencies:
    """Return the dependencies of an integration test, from the environment configuration."""
    return integration_test_dependencies()


@pytest.fixture(autouse=True)
def skip_if_not_production(request: pytest.FixtureRequest) -> None:
    """Skip a test marked with `production` when the service is not a production one.

    The dependencies are resolved lazily, so that the tests without the marker do not require
    the environment configuration.
    """
    if request.node.get_closest_marker("production") is None:
        return

    dependencies = request.getfixturevalue("dependencies")
    if "dev" in dependencies.url or "test" in dependencies.url:
        pytest.skip("Skipping integration test. Not supported on staging.")
